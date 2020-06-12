import os, sys, pathlib, logging

from PyQt5 import QtGui, QtWidgets

from ClientMainWindow import ClientMainWindow



def main():
    logging.basicConfig(filename=os.path.join(pathlib.Path(__file__).parent.absolute(), 'BBQTools.log'), format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO)

    app = QtWidgets.QApplication([])

    client = ClientMainWindow()
    client.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()