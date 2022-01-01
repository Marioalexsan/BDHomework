from pygubuapp import PygubuApp
import mysql.connector as sqlcon
import tkinter


# Overrides callbacks for the generated pygubuapp.py
# This exists because I don't want to edit generated files
class BDApp(PygubuApp):
    def __init__(self):
        super().__init__()
        self.dbconnection = None
        self.dbcursor = None
        self.swap_frame('login_panel')
        self.current_table = ''

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
                autocommit=False,
                get_warnings=True,
                raise_on_warnings=False,
                buffered=True,
            )

            if not self.dbconnection.is_connected():
                raise Exception

            self.dbcursor = self.dbconnection.cursor(buffered=True)

            self.dbcursor.execute('USE BDHOMEWORK;')

            print('Connected!')

            self.swap_frame('table_list_frame')

        except Exception as e:
            self.dbconnection = None
            print('Unable to connect! Reason:', e)
            return

    def on_tableopen(self):
        listbox = self.get_widget('table_list')
        selected = listbox.curselection()

        if selected[0] is None:
            print('Select a table from the list!')
            return

        table_name = listbox.get(selected[0])

        print('You selected table', table_name)

        self.current_table = table_name

        self.prepare_table_view()
        self.swap_frame('table_view_frame')

        pass

    def on_cancelchanges(self):
        print('Rolled back changes.')
        self.dbcursor.execute('ROLLBACK;')
        self.swap_frame('table_list_frame')
        pass

    def on_savechanges(self):
        print('Commited changes.')
        self.dbcursor.execute('COMMIT;')
        self.swap_frame('table_list_frame')
        pass

    def on_logoff(self):
        self.dbconnection.close()
        self.dbconnection = None
        self.dbcursor = None
        print('Disconnected!')

        self.swap_frame('login_panel')

        pass

    # Helper Methods #

    def prepare_table_view(self):
        self.get_widget('table_name')['text'] = 'Viewing table ' + self.current_table

    def get_widget(self, name):
        return self.builder.get_object(name)

    def swap_frame(self, name):
        for k, v in self.mainwindow.children.items():
            v.pack_forget()

        # TODO: Check if named widget is from Toplevel
        self.builder.get_object(name).pack()

        if name == 'table_list_frame':
            print('Fetching tables')
            self.dbcursor.execute('SHOW TABLES;')

            results = self.dbcursor.fetchall()

            table_list = self.get_widget('table_list')
            table_list.delete(0, 9999)

            index = 0
            for sql_tuple in results:
                table_list.insert(index, sql_tuple[0])

            self.current_table = ''

        elif name == 'table_view_frame':
            print('Viewing table', self.current_table)
            self.get_widget('table_name')['text'] = 'Viewing table ' + self.current_table

            self.dbcursor.execute('START TRANSACTION;')

            self.dbcursor.execute('DESCRIBE ' + self.current_table + ';')

            table_info = self.dbcursor.fetchall()
            table_attr_count = len(table_info)

            self.dbcursor.execute('SELECT * FROM ' + self.current_table + ';')

            table_tuples = self.dbcursor.fetchall()
            table_tuple_count = len(table_tuples)

            runtime_table = self.get_widget('runtime_table')

            for child in runtime_table.winfo_children():
                child.destroy()

            for x in range(0, table_attr_count):
                cell = tkinter.Label(runtime_table, text=str(table_info[x][0]))
                cell.grid(column=x, row=0)

            for y in range(0, table_tuple_count):
                for x in range(0, table_attr_count):
                    cell = tkinter.Label(runtime_table, text=str(table_tuples[y][x]))
                    cell.grid(column=x, row=(y + 1))
