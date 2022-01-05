from tkinter import ttk
from typing import Optional

import mysql.connector

from pygubuapp import PygubuApp
from sqlproxy import MySQLTableProxy, TableRow
import mysql.connector as sqlcon
import tkinter


# Overrides callbacks for the generated pygubuapp.py
# This exists because I don't want to edit generated files
class BDApp(PygubuApp):
    ROW_NEWROW = -1
    VALUE_AUTOASSIGN = '<Primary Key>'

    def __init__(self):
        super().__init__()
        self.dbconnection = None
        self.cursor = None
        self.row_editing = None
        self.table_proxy: Optional[MySQLTableProxy] = None
        self.transaction_active = False
        self.row_widgets = []

        self.initialize_frame = {
            'login_panel': self.init_login_frame,
            'table_list_frame': self.init_table_list,
            'table_view_frame': self.init_table_view,
            'table_row_edit_frame': self.init_table_row_edit
        }

        self.swap_frame('login_panel')

    # Callbacks #

    def on_accessdatabase(self):
        user = self.get_widget('user_entry').get()
        password = self.get_widget('password_entry').get()
        host = self.get_widget('host_entry').get()
        port = self.get_widget('port_entry').get()

        try:
            self.dbconnection = sqlcon.connect(
                host=host,
                port=int(port),
                user=user,
                password=password,
                autocommit=True,  # Will use START TRANSACTION when necessary
                get_warnings=True,
                raise_on_warnings=False,
                connection_timeout=2,
                buffered=True,
            )

            self.cursor = self.dbconnection.cursor(buffered=True)
            self.cursor.execute('USE BDHOMEWORK;')

            self.swap_frame('table_list_frame')

        except Exception as e:
            self.dbconnection = None
            self.cursor = None
            self.get_widget('login_status')['text'] = 'Status: ' + str(e)
            return

    def on_tableopen(self):
        listbox = self.get_widget('table_list')
        selected = listbox.curselection()

        if len(selected) != 1:
            return

        table_name = listbox.get(selected[0])[0]

        self.table_proxy = MySQLTableProxy(self.cursor, 'bdhomework', table_name)
        self.swap_frame('table_view_frame')

    def on_cancelchanges(self):
        print('Rolled back changes.')
        self.try_rollback()
        self.swap_frame('table_list_frame')
        pass

    def on_savechanges(self):
        print('Commited changes.')
        self.try_commit()
        self.swap_frame('table_list_frame')
        pass

    def on_logoff(self):
        self.dbconnection.close()
        self.dbconnection = None
        self.cursor = None

        self.swap_frame('login_panel')
        pass

    def on_cancelrowchanges(self):
        self.row_editing = None
        self.swap_frame('table_view_frame')

        print('Exited row change')

    def on_saverowchanges(self):
        widget_values = []

        for widget in self.row_widgets:
            if isinstance(widget, ttk.OptionMenu):
                widget_values.append(widget.getvar(widget['textvariable']))
            elif isinstance(widget, tkinter.Entry):
                widget_values.append(widget.get())
            else:
                raise RuntimeError

        nullval = MySQLTableProxy.VALUE_NULL
        widget_values = [None if value == nullval else value for value in widget_values]

        row = TableRow()
        row.attributes = [row[0] for row in self.table_proxy.get_attributes()]
        row.values = widget_values

        if self.row_editing == BDApp.ROW_NEWROW:
            retval = self.table_proxy.add_row(row)
        else:
            retval = self.table_proxy.edit_row(self.row_editing, row)

        if retval == MySQLTableProxy.RESULT_OK:
            retval = 'Success!'

        self.get_widget('row_edit_status')['text'] = 'Status: ' + retval
        print('Saving row changes')

    # Runtime Callbacks #

    def on_deleterow(self, row):
        self.table_proxy.delete_row(row)
        self.swap_frame('table_view_frame')

    def on_newrow(self):
        self.row_editing = BDApp.ROW_NEWROW
        self.swap_frame('table_row_edit_frame')

    def on_editrow(self, row):
        self.row_editing = row
        self.swap_frame('table_row_edit_frame')

    # Helper Methods #

    def get_widget(self, name):
        return self.builder.get_object(name)

    # Frame Initializers #

    def init_login_frame(self):
        self.get_widget('login_status')['text'] = 'Status: Waiting for login'

    def init_table_list(self):
        self.cursor.execute('SHOW TABLES;')
        results = self.cursor.fetchall()

        table_list = self.get_widget('table_list')
        table_list.delete(0, 9999)
        table_list.insert(0, *results)

        self.table_proxy = None

    def init_table_view(self):
        self.row_editing = None
        self.try_transaction()

        self.get_widget('table_name')['text'] = 'Viewing table ' + self.table_proxy.table

        runtime_table = self.get_widget('runtime_table')

        # Clear runtime table
        for child in runtime_table.winfo_children():
            child.destroy()

        attributes = self.table_proxy.get_attributes()
        tuples = self.table_proxy.get_tuples()

        # Add table attributes and their types as row 0 through 1
        for x in range(0, len(attributes)):
            attr_info = self.table_proxy.get_attr_info(x)

            tkinter.Label(runtime_table, text=attr_info.type).grid(column=x, row=0, padx=5, pady=5)
            tkinter.Label(runtime_table, text=attr_info.name).grid(column=x, row=1, padx=5, pady=5)

        # Add table tuples as rows 2 through N + 1
        for y in range(0, len(tuples)):
            for x in range(0, len(attributes)):
                tuple_data = tuples[y][x]

                if tuple_data is None:
                    tuple_data = MySQLTableProxy.VALUE_NULL

                tkinter.Label(runtime_table, text=str(tuple_data)).grid(column=x, row=(y + 2), padx=5, pady=5)

            edit = tkinter.Button(runtime_table, text='Edit')
            delete = tkinter.Button(runtime_table, text='Delete')

            edit.grid(column=len(attributes), row=(y + 2), padx=5, pady=5)
            delete.grid(column=(len(attributes) + 1), row=(y + 2), padx=5, pady=5)

            edit.bind('<Button>', lambda event, row=y: self.on_editrow(row))
            delete.bind('<Button>', lambda event, row=y: self.on_deleterow(row))

        # Add edit row
        for x in range(0, len(attributes)):
            tkinter.Label(runtime_table, text='---').grid(column=x, row=(len(tuples) + 2), padx=5, pady=5)

        add_entry = tkinter.Button(runtime_table, text='Add Entry')
        add_entry.grid(column=len(attributes), row=(len(tuples) + 2), padx=5, pady=5)
        add_entry.bind('<Button>', lambda event: self.on_newrow())

    def init_table_row_edit(self):
        self.get_widget('row_edit_status')['text'] = 'Status: Just Entered Menu'

        if self.row_editing == BDApp.ROW_NEWROW:
            disp_text = 'Adding new row:'
        else:
            disp_text = 'Editing row {}:'.format(self.row_editing)

        self.get_widget('table_row_name')['text'] = disp_text

        attributes = self.table_proxy.get_attributes()
        tuples = self.table_proxy.get_tuples()

        runtime_row = self.get_widget('runtime_row')

        # Clear runtime row
        for child in runtime_row.winfo_children():
            child.destroy()

        # Add table attributes and their types as row 0 through 1
        for x in range(0, len(attributes)):
            attr_info = self.table_proxy.get_attr_info(x)

            cell_name = tkinter.Label(runtime_row, text=attr_info.name)
            cell_type = tkinter.Label(runtime_row, text=attr_info.type)
            cell_name.grid(column=x, row=0, padx=5, pady=5)
            cell_type.grid(column=x, row=1, padx=5, pady=5)

        self.row_widgets.clear()

        # Add entries, option menu, etc.
        for x in range(0, len(attributes)):
            attr_info = self.table_proxy.get_attr_info(x)

            if attr_info.is_foreign_key:
                valid_values = attr_info.get_fk_values(self.cursor)
                valid_values.sort()

                wanted_index = 0

                if self.row_editing != BDApp.ROW_NEWROW:
                    value = self.table_proxy.get_tuples()[self.row_editing][x]

                    if value is None:
                        value = MySQLTableProxy.VALUE_NULL

                    wanted_index = valid_values.index(value)

                cell = ttk.OptionMenu(runtime_row, tkinter.StringVar(), valid_values[wanted_index], *valid_values)
            else:
                cell = tkinter.Entry(runtime_row)

                if self.row_editing != BDApp.ROW_NEWROW:
                    last_value = self.table_proxy.get_tuples()[self.row_editing][x]

                    if last_value is None:
                        last_value = MySQLTableProxy.VALUE_NULL

                    cell.insert(0, last_value)

                if self.row_editing == BDApp.ROW_NEWROW and attr_info.is_primary_key:
                    next_pk = self.table_proxy.get_next_pk()

                    if next_pk is not None:
                        autoassign_value = str(next_pk)
                    else:
                        autoassign_value = '<Can\'t autoassign>'

                    cell.delete(0, 9999)
                    cell.insert(0, autoassign_value)

                if attr_info.is_primary_key:
                    cell.configure(state='disabled')

            cell.grid(column=x, row=2, padx=5, pady=5)
            self.row_widgets.append(cell)

    def swap_frame(self, name):
        if name in self.initialize_frame and callable(self.initialize_frame[name]):
            self.initialize_frame[name]()

        for k, v in self.mainwindow.children.items():
            v.pack_forget()

        target = self.builder.get_object(name)

        if target not in self.mainwindow.winfo_children():
            print('Warning: Swapping to a frame that isn\'t a scene!')

        target.pack()

    def try_transaction(self):
        if self.transaction_active:
            return

        self.cursor.execute('START TRANSACTION;')
        self.transaction_active = True

    def try_commit(self):
        if not self.transaction_active:
            return

        self.cursor.execute('COMMIT;')
        self.transaction_active = False

    def try_rollback(self):
        if not self.transaction_active:
            return

        self.cursor.execute('ROLLBACK;')
        self.transaction_active = False


if __name__ == '__main__':
    app = BDApp()
    app.run()
