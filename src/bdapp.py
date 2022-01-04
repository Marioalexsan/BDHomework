from tkinter import ttk
from typing import Optional

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
        self.transaction_active = None

        self.initialize_frame = {
            'table_list_frame': self.init_table_list,
            'table_view_frame': self.init_table_view,
            'table_row_edit_frame': self.init_table_row_edit
        }

        self.row_widgets = []

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
                buffered=True,
            )

            if not self.dbconnection.is_connected():
                raise Exception

            self.cursor = self.dbconnection.cursor(buffered=True)
            self.cursor.execute('USE BDHOMEWORK;')

            print('Connected!')

            self.swap_frame('table_list_frame')

        except Exception as e:
            self.dbconnection = None
            self.cursor = None
            print('Unable to connect! Reason:', e)
            return

    def on_tableopen(self):
        listbox = self.get_widget('table_list')
        selected = listbox.curselection()

        if len(selected) != 1:
            print('Select a table from the list!')
            return

        table_name = listbox.get(selected[0])

        print('You selected table', table_name)

        self.table_proxy = MySQLTableProxy(self.cursor, 'bdhomework', table_name)

        self.swap_frame('table_view_frame')

        pass

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
        print('Disconnected!')

        self.swap_frame('login_panel')

        pass

    def on_cancelrowchanges(self):
        print('Cancelled row changes')
        self.row_editing = None
        self.swap_frame('table_view_frame')

    def on_saverowchanges(self):
        print('Saved row changes')

        widget_values = []

        for widget in self.row_widgets:
            if isinstance(widget, ttk.OptionMenu):
                widget_values.append(widget.getvar(widget['textvariable']))
            elif isinstance(widget, tkinter.Entry):
                widget_values.append(widget.get())
            else:
                raise RuntimeError

        for i in range(0, len(widget_values)):
            if widget_values[i] == MySQLTableProxy.VALUE_NONE:
                widget_values[i] = None

        row = TableRow()
        row.attributes = [row[0] for row in self.table_proxy.get_cache().attributes]
        row.values = widget_values

        retval = None

        if self.row_editing == BDApp.ROW_NEWROW:
            retval = self.table_proxy.add_row(row)

        elif self.row_editing is not None:
            retval = self.table_proxy.edit_row(self.row_editing, row)

        if retval == MySQLTableProxy.RESULT_OK:
            retval = 'Success!'

        self.get_widget('row_edit_status')['text'] = 'Status: ' + retval

    # Runtime Callbacks #

    def on_deleterow(self, row):
        self.cursor.execute('')

        print('You\'re deleting a row now')

        self.table_proxy.delete_row(row)
        self.swap_frame('table_view_frame')

    def on_newrow(self):
        print('You\'re creating a row now')
        self.row_editing = BDApp.ROW_NEWROW
        self.swap_frame('table_row_edit_frame')

    def on_editrow(self, row):
        print('You selected row ', row)
        self.row_editing = row
        self.swap_frame('table_row_edit_frame')

    # Helper Methods #

    def get_widget(self, name):
        return self.builder.get_object(name)

    # Frame Initializers #

    def init_table_list(self):
        print('Fetching tables')
        self.cursor.execute('SHOW TABLES;')

        results = self.cursor.fetchall()

        table_list = self.get_widget('table_list')
        table_list.delete(0, 9999)

        index = 0
        for sql_tuple in results:
            table_list.insert(index, sql_tuple[0])

        self.table_proxy = None

    def init_table_view(self):
        self.row_editing = None

        self.try_transaction()

        print('Viewing table', self.table_proxy.table)

        self.get_widget('table_name')['text'] = 'Viewing table ' + self.table_proxy.table

        runtime_table = self.get_widget('runtime_table')

        # Clear runtime table
        for child in runtime_table.winfo_children():
            child.destroy()

        attributes = self.table_proxy.get_cache().attributes
        tuples = self.table_proxy.get_cache().tuples

        attr_count = len(attributes)
        tuple_count = len(tuples)

        cache = self.table_proxy.get_cache()

        # Add table attributes and their types as row 0 through 1
        for x in range(0, attr_count):
            attr_info = cache.get_attr_info(x)
            attr_type = attr_info.type
            attr_name = attr_info.name

            if isinstance(attr_type, bytes) or isinstance(attr_type, bytearray):
                attr_type = attr_type.decode('utf-8')

            tkinter.Label(runtime_table, text=attr_name).grid(column=x, row=0, padx=5, pady=5)
            tkinter.Label(runtime_table, text=attr_type).grid(column=x, row=1, padx=5, pady=5)

        # Add table tuples as rows 2 through N + 1
        for y in range(0, tuple_count):
            for x in range(0, attr_count):
                tuple_data = tuples[y][x]

                if tuple_data is None:
                    tuple_data = MySQLTableProxy.VALUE_NONE

                tkinter.Label(runtime_table, text=str(tuple_data)).grid(column=x, row=(y + 2), padx=5, pady=5)

            button = tkinter.Button(runtime_table, text='Edit')
            button.grid(column=attr_count, row=(y + 2), padx=5, pady=5)
            button.bind('<Button>', lambda event, row=y: self.on_editrow(row))

            button = tkinter.Button(runtime_table, text='Delete')
            button.grid(column=(attr_count + 1), row=(y + 2), padx=5, pady=5)
            button.bind('<Button>', lambda event, row=y: self.on_deleterow(row))

        # Add dummy row for style, and button for adding new entries

        for x in range(0, attr_count):
            tkinter.Label(runtime_table, text='---').grid(column=x, row=(tuple_count + 2), padx=5, pady=5)

        button = tkinter.Button(runtime_table, text='Add Entry')
        button.grid(column=attr_count, row=(tuple_count + 2), padx=5, pady=5)
        button.bind('<Button>', lambda event: self.on_newrow())

    def init_table_row_edit(self):
        print('Working on row', self.row_editing)

        self.get_widget('row_edit_status')['text'] = 'Status: Just Entered Menu'

        disp_text = ''

        if self.row_editing == BDApp.ROW_NEWROW:
            disp_text += 'Adding new row '
        elif self.row_editing is not None:
            disp_text += 'Doing something on row '
        else:
            disp_text += 'Editing row '

        if self.row_editing != -1:
            disp_text += str(self.row_editing)

        disp_text += ':'

        self.get_widget('table_row_name')['text'] = disp_text

        cache = self.table_proxy.get_cache()

        attr_count = len(cache.attributes)

        runtime_row = self.get_widget('runtime_row')

        # Clear runtime row
        for child in runtime_row.winfo_children():
            child.destroy()

        # Add table attributes and their types as row 0 through 1
        for x in range(0, attr_count):
            attr_info = cache.get_attr_info(x)

            cell = tkinter.Label(runtime_row, text=str(attr_info.name))
            cell.grid(column=x, row=0, padx=5, pady=5)

            attr_type = attr_info.type

            if isinstance(attr_type, bytes) or isinstance(attr_type, bytearray):
                attr_type = attr_type.decode('utf-8')

            cell = tkinter.Label(runtime_row, text=attr_type)
            cell.grid(column=x, row=1, padx=5, pady=5)

        self.row_widgets.clear()

        for x in range(0, attr_count):
            attr_info = self.table_proxy.get_attr_info(x)

            if attr_info.is_foreign_key:
                valid_values = attr_info.get_fk_values(self.cursor)

                wanted_index = 0
                if self.row_editing != BDApp.ROW_NEWROW:
                    value = self.table_proxy.get_cache().tuples[self.row_editing][x]

                    if value is None:
                        value = MySQLTableProxy.VALUE_NONE

                    wanted_index = valid_values.index(value)

                cell = ttk.OptionMenu(runtime_row, tkinter.StringVar(), valid_values[wanted_index], *valid_values)
            else:
                cell = tkinter.Entry(runtime_row)

                if self.row_editing != BDApp.ROW_NEWROW:
                    last_value = self.table_proxy.get_cache().tuples[self.row_editing][x]

                    if last_value is None:
                        last_value = MySQLTableProxy.VALUE_NONE

                    cell.insert(0, last_value)

                if self.row_editing == BDApp.ROW_NEWROW and attr_info.is_primary_key:
                    next_pk = self.table_proxy.get_next_pk()

                    autoassign_value = '<Can\'t autoassign>'

                    if next_pk is not None:
                        autoassign_value = str(next_pk)

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

        # TODO: Check if named widget is from Toplevel
        self.builder.get_object(name).pack()

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
