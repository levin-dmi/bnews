import unittest

from bnews import PAGE_LIST, parsing_page


class TestEncodingNews(unittest.TestCase):
    def test_bridgesport(self):
        """
        Test that it can bridgesport.ru encoding
        """

        data = '<table class="contentpaneopen"><tr>' \
               '<td valign="top" colspan="2" class="createdate">' \
               '.08.2019 г.</td></tr>' \
               '<tr><td valign="top" colspan="2">' \
               '<center><h3>  \rthise\ntest\r\ncomplete<br />' \
               '</td></tr></table>'
        result = parsing_page(data, PAGE_LIST['Bridgesport'])
        self.assertEqual(result, ['thise test complete'])


if __name__ == '__main__':
    unittest.main()
