import pyxbmct.addonwindow as pyxbmct
import plex
from common import printDebug

printDebug=printDebug("PleXBMC", "plex_signin")

class plex_signin(pyxbmct.AddonFullWindow):
    def __init__(self, title=''):
        """Class constructor"""
        # Call the base class' constructor.
        super(plex_signin, self).__init__(title)
        # Set width, height and the grid parameters
        self.setGeometry(600, 400, 6, 6)
        # Call set controls method
        self.set_controls()
        # Call set navigation method.
        self.set_navigation()
        # Connect Backspace button to close our addon.
        self.connect(pyxbmct.ACTION_NAV_BACK, self.close)

    def set_authentication_target(self, plex_network):
        self.plex_network = plex_network
        
    def set_controls(self):
        """Set up UI controls"""
        # Description Text
        self.description = pyxbmct.TextBox()
        self.placeControl(self.description, 1 , 1 , columnspan=4)
        
        #Username label
        self.name_label = pyxbmct.Label('Username:')
        self.placeControl(self.name_label, 2, 1)
        #username entry box
        self.name_field = pyxbmct.Edit('')
        self.placeControl(self.name_field, 2, 2, columnspan=2)

        #Password Label
        self.password_label = pyxbmct.Label('Password:')
        self.placeControl(self.password_label, 3, 1)
        
        #Password entry box
        self.password_field = pyxbmct.Edit('', isPassword=True)
        self.placeControl(self.password_field, 3, 2, columnspan=2)

        # Cancel button
        self.cancel_button = pyxbmct.Button('Cancel')
        self.placeControl(self.cancel_button,5, 1)
        # Cancel button closes window
        self.connect(self.cancel_button, self.close)
        
        # Submit button
        self.submit_button = pyxbmct.Button('Submit')
        self.placeControl(self.submit_button, 5, 4)
        # Submit button to get token

        # Manual button
        self.manual_button = pyxbmct.Button('Manual')
        self.placeControl(self.manual_button, 5, 4)

        # PIN button
        self.pin_button = pyxbmct.Button('Use PIN')
        self.placeControl(self.pin_button, 5, 2, columnspan=2)

        # Submit button to get token
        self.connect(self.submit_button, lambda: self.submit())
        self.connect(self.manual_button, lambda: self.display_manual())
        self.connect(self.pin_button, lambda: self.display_pin())

        self.display_pin()

    def display_pin(self):
        self.description.setText('From your computer, go to http://plex.tv/pin and enter the code below')
        self.name_label.setVisible(False)
        self.password_label.setVisible(False)
        self.name_field.setVisible(False)
        self.password_field.setVisible(False)
        self.manual_button.setVisible(True)
        self.submit_button.setVisible(False)
        self.pin_button.setVisible(False)
        self.cancel_button.setNavigation(self.manual_button, self.manual_button, self.manual_button,self.manual_button)
        self.setFocus(self.manual_button)
        
    def display_manual(self):
        self.description.setText('Please enter your myplex details below')
        self.name_label.setVisible(True)
        self.password_label.setVisible(True)
        self.name_field.setVisible(True)
        self.password_field.setVisible(True)
        self.manual_button.setVisible(False)
        self.submit_button.setVisible(True)
        self.pin_button.setVisible(True)
        self.cancel_button.setNavigation(self.password_field, self.name_field, self.submit_button,self.pin_button)
        self.pin_button.setNavigation(self.password_field, self.name_field, self.cancel_button,self.submit_button)
        self.submit_button.setNavigation(self.password_field, self.name_field, self.pin_button,self.cancel_button)
        self.setFocus(self.name_field)

    def submit(self):
        token = self.plex_network.sign_into_myplex(self.name_field.getText(), self.password_field.getText())
        
        if token is not None:
            printDebug("Successfully signed in")
            
            self.close()
        else:
            printDebug("Not Successful signed in")
            self.close()
        
    def set_navigation(self):
        """Set up keyboard/remote navigation between controls."""
        self.name_field.controlUp(self.submit_button)
        self.name_field.controlDown(self.password_field)
        self.password_field.controlUp(self.name_field)
        self.password_field.controlDown(self.submit_button)
        self.manual_button.controlLeft(self.cancel_button)
        self.manual_button.controlRight(self.cancel_button)
        # Set initial focus.
