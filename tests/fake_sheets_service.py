"""googleapiclient'ning spreadsheets().values() obyektiga mos, tarmoqsiz
ishlaydigan soxta implementatsiya - faqat sheets.py'ni sinash uchun."""


class _FakeRequest:
    def __init__(self, fn):
        self._fn = fn

    def execute(self):
        return self._fn()


class FakeValuesService:
    def __init__(self):
        self.sheets = {}  # sheet_name -> list[list]

    @staticmethod
    def _sheet_name(range_str):
        return range_str.split("!")[0]

    def get(self, spreadsheetId, range, valueRenderOption=None):
        # valueRenderOption e'tiborsiz qoldiriladi - bu soxta implementatsiya
        # hech qachon katakchalarni formatlamaydi, shuning uchun xom/
        # formatlangan farqi yo'q (haqiqiy Sheets API'da esa muhim -
        # sheets.py shu farqni UNFORMATTED_VALUE bilan hal qiladi).
        def _do():
            sheet = self._sheet_name(range)
            return {"values": [list(row) for row in self.sheets.get(sheet, [])]}
        return _FakeRequest(_do)

    def append(self, spreadsheetId, range, valueInputOption, insertDataOption, body):
        def _do():
            sheet = self._sheet_name(range)
            self.sheets.setdefault(sheet, []).extend(body["values"])
            return {}
        return _FakeRequest(_do)

    def update(self, spreadsheetId, range, valueInputOption, body):
        def _do():
            sheet_name, cell_range = range.split("!")
            start_cell = cell_range.split(":")[0]
            row_number = int("".join(ch for ch in start_cell if ch.isdigit()))
            data_index = row_number - 2  # 1-qator sarlavha, A2 = data_index 0
            rows = self.sheets.setdefault(sheet_name, [])
            while len(rows) <= data_index:
                rows.append([])
            rows[data_index] = body["values"][0]
            return {}
        return _FakeRequest(_do)
