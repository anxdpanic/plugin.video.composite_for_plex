import pyxbmct.addonwindow as pyxbmct
import resources.lib.plex
from resources.lib.common import PrintDebug, GLOBAL_SETUP
import xbmc

log_print = PrintDebug("PleXBMC", "plex_signin")


class PlexSignin(pyxbmct.AddonFullWindow):
    def __init__(self, title=''):
        """Class constructor"""
        # Call the base class' constructor.
        super(PlexSignin, self).__init__(title)
        # Set width, height and the grid parameters
        self.setGeometry(600, 400, 6, 6)
        # Call set controls method
        self.set_controls()
        # Call set navigation method.
        self.set_navigation()
        # Connect Backspace button to close our addon.
        self.connect(pyxbmct.ACTION_NAV_BACK, self.close)
        self.plex_network = None
        self.identifier = None

    def start(self):
        self.display_pin()
        self.doModal()

    def set_authentication_target(self, plex_network):
        self.plex_network = plex_network

    def set_controls(self):
        """Set up UI controls"""
        # Description Text
        self.description = pyxbmct.TextBox()
        self.placeControl(self.description, 1, 1, columnspan=4)

        # Username label
        self.name_label = pyxbmct.Label('Username:')
        self.placeControl(self.name_label, 2, 1)
        # username entry box
        self.name_field = pyxbmct.Edit('')
        self.placeControl(self.name_field, 2, 2, columnspan=2)

        # Password Label
        self.password_label = pyxbmct.Label('Password:')
        self.placeControl(self.password_label, 3, 1)
        # Password entry box
        self.password_field = pyxbmct.Edit('', isPassword=True)
        self.placeControl(self.password_field, 3, 2, columnspan=2)

        # Cancel button
        self.cancel_button = pyxbmct.Button('Cancel')
        self.placeControl(self.cancel_button, 5, 1)
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

        # PIN button
        self.submit_pin_button = pyxbmct.Button('Done')
        self.placeControl(self.submit_pin_button, 5, 2, columnspan=2)

        # Submit button to get token
        self.connect(self.submit_button, lambda: self.submit())
        self.connect(self.manual_button, lambda: self.display_manual())
        self.connect(self.pin_button, lambda: self.display_pin())
        self.connect(self.submit_pin_button, lambda: self.submit_pin())

        # set up failure message
        self.error_cross = pyxbmct.Image("%s/resources/media/error.png" % GLOBAL_SETUP['__cwd__'], aspectRatio=2)
        self.placeControl(self.error_cross, 4, 2)
        self.error_message = pyxbmct.Label("Unable to Login")
        self.placeControl(self.error_message, 4, 3, columnspan=2, rowspan=2)
        self.error_cross.setVisible(False)
        self.error_message.setVisible(False)

        self.digit_one = pyxbmct.Image("%s/resources/media/-.png" % GLOBAL_SETUP['__cwd__'], aspectRatio=2)
        self.digit_two = pyxbmct.Image("%s/resources/media/-.png" % GLOBAL_SETUP['__cwd__'], aspectRatio=2)
        self.digit_three = pyxbmct.Image("%s/resources/media/-.png" % GLOBAL_SETUP['__cwd__'], aspectRatio=2)
        self.digit_four = pyxbmct.Image("%s/resources/media/-.png" % GLOBAL_SETUP['__cwd__'], aspectRatio=2)

        self.placeControl(self.digit_one, 3, 1)
        self.placeControl(self.digit_two, 3, 2)
        self.placeControl(self.digit_three, 3, 3)
        self.placeControl(self.digit_four, 3, 4)

    def display_failure(self, state=True):
        if state:
            self.error_cross.setVisible(True)
            self.error_message.setVisible(True)
        else:
            self.error_cross.setVisible(False)
            self.error_message.setVisible(False)

    def display_pin(self, failure=False):
        if failure:
            self.display_failure()
        else:
            self.display_failure(False)

        self.description.setText('From your computer, go to http://plex.tv/pin and enter the code below.  Then click done')
        self.name_label.setVisible(False)
        self.password_label.setVisible(False)
        self.name_field.setVisible(False)
        self.password_field.setVisible(False)
        self.manual_button.setVisible(True)
        self.submit_button.setVisible(False)
        self.pin_button.setVisible(False)
        self.submit_pin_button.setVisible(True)
        self.cancel_button.setNavigation(self.submit_pin_button, self.manual_button, self.manual_button, self.submit_pin_button )
        self.submit_pin_button.setNavigation(self.manual_button, self.cancel_button, self.cancel_button, self.manual_button)
        self.manual_button.setNavigation(self.cancel_button, self.submit_pin_button, self.submit_pin_button, self.cancel_button)

        self.data = self.plex_network.get_signin_pin()

        digits = self.data['code']
        self.identifier = self.data['id']
        self.digit_one.setVisible(True)
        self.digit_two.setVisible(True)
        self.digit_three.setVisible(True)
        self.digit_four.setVisible(True)

        self.digit_one.setImage("%s/resources/media/%s.png" % (GLOBAL_SETUP['__cwd__'], digits[0].lower()))
        self.digit_two.setImage("%s/resources/media/%s.png" % (GLOBAL_SETUP['__cwd__'], digits[1].lower()))
        self.digit_three.setImage("%s/resources/media/%s.png" % (GLOBAL_SETUP['__cwd__'], digits[2].lower()))
        self.digit_four.setImage("%s/resources/media/%s.png" % (GLOBAL_SETUP['__cwd__'], digits[3].lower()))

        self.setFocus(self.submit_pin_button)

    def display_manual(self, failure=False):
        self.description.setText('Please enter your myplex details below')
        self.name_label.setVisible(True)
        self.password_label.setVisible(True)
        self.name_field.setVisible(True)
        self.password_field.setVisible(True)
        self.manual_button.setVisible(False)
        self.submit_button.setVisible(True)
        self.pin_button.setVisible(True)
        self.cancel_button.setNavigation(self.password_field, self.name_field, self.submit_button, self.pin_button)
        self.pin_button.setNavigation(self.password_field, self.name_field, self.cancel_button, self.submit_button)
        self.submit_button.setNavigation(self.password_field, self.name_field, self.pin_button, self.cancel_button)
        self.digit_one.setVisible(False)
        self.digit_two.setVisible(False)
        self.digit_three.setVisible(False)
        self.digit_four.setVisible(False)
        self.submit_pin_button.setVisible(False)        
        self.setFocus(self.name_field)

        if failure:
            self.display_failure()
        else:
            self.display_failure(False)

    def submit(self):
        token = self.plex_network.sign_into_myplex(self.name_field.getText(), self.password_field.getText())

        if token is not None:
            self.name_label.setVisible(False)
            self.password_label.setVisible(False)
            self.name_field.setVisible(False)
            self.password_field.setVisible(False)
            self.manual_button.setVisible(False)
            self.cancel_button.setVisible(False)
            self.submit_button.setVisible(False)
            self.pin_button.setVisible(False)
            # tick mark
            self.tick = pyxbmct.Image("%s/resources/media/tick.png" % GLOBAL_SETUP['__cwd__'], aspectRatio=2)
            self.placeControl(self.tick, 2, 2, columnspan=2, rowspan=2)

            self.description.setText('Successfully Signed In')
            xbmc.sleep(2000)

            log_print("Successfully signed in")

            self.close()
        else:
            log_print("Not Successful signed in")
            self.display_manual(True)

    def submit_pin(self):
        result = self.plex_network.check_signin_status(self.identifier)

        if result:
            self.digit_one.setVisible(False)
            self.digit_two.setVisible(False)
            self.digit_three.setVisible(False)
            self.digit_four.setVisible(False)
            self.manual_button.setVisible(False)
            self.cancel_button.setVisible(False)
            self.submit_button.setVisible(False)
            self.pin_button.setVisible(False)
            self.submit_pin_button.setVisible(False)
            # tick mark
            self.tick = pyxbmct.Image("%s/resources/media/tick.png" % GLOBAL_SETUP['__cwd__'], aspectRatio=2)
            self.placeControl(self.tick, 2, 2, columnspan=2, rowspan=2)

            self.description.setText('Successfully Signed In')
            xbmc.sleep(2000)

            log_print("Successfully signed in")

            self.close()
        else:
            log_print("Not Successful signed in")
            self.display_pin(True)

    def set_navigation(self):
        """Set up keyboard/remote navigation between controls."""
        self.name_field.controlUp(self.submit_button)
        self.name_field.controlDown(self.password_field)
        self.password_field.controlUp(self.name_field)
        self.password_field.controlDown(self.submit_button)
        # Set initial focus.


class PlexManage(pyxbmct.AddonFullWindow):
    def __init__(self, title=''):
        """Class constructor"""
        # Call the base class' constructor.
        super(PlexManage, self).__init__(title)
        # Set width, height and the grid parameters
        self.setGeometry(600, 400, 6, 6)
        # Call set controls method
        self.set_controls()
        # Call set navigation method.
        self.set_navigation()
        # Connect Backspace button to close our addon.
        self.connect(pyxbmct.ACTION_NAV_BACK, self.close)
        self.plex_network = None

    def start(self):
        self.gather_plex_information()
        self.setFocus(self.cancel_button)
        self.doModal()

    def gather_plex_information(self):
        user = self.plex_network.get_myplex_information()

        self.name_field.setText(user['username'])
        self.email_field.setText(user['email'])
        self.plexpass_field.setText(user['plexpass'])
        self.membersince_field.setText(user['membersince'])
        if user['thumb']:
            self.thumb.setImage(user['thumb'])

    def set_authentication_target(self, plex_network):
        self.plex_network = plex_network

    def set_controls(self):
        """Set up UI controls"""
        # Description Text
        self.description = pyxbmct.TextBox()
        self.placeControl(self.description, 2, 0, columnspan=4)

        # Username label
        self.name_label = pyxbmct.Label('Username:')
        self.placeControl(self.name_label, 1, 1)

        # username text box
        self.name_field = pyxbmct.TextBox()
        self.placeControl(self.name_field, 1, 2, columnspan=2)

        # thumb label
        self.thumb = pyxbmct.Image('', aspectRatio=2)
        self.placeControl(self.thumb, 1, 4)

        # Email Label
        self.email_label = pyxbmct.Label('Email:')
        self.placeControl(self.email_label, 2, 1)
        # Email text box
        self.email_field = pyxbmct.TextBox()
        self.placeControl(self.email_field, 2, 2, columnspan=2)

        # plexpass Label
        self.plexpass_label = pyxbmct.Label('Plexpass:')
        self.placeControl(self.plexpass_label, 3, 1)
        # Password entry box
        self.plexpass_field = pyxbmct.TextBox()
        self.placeControl(self.plexpass_field, 3, 2, columnspan=2)

        # membersince Label
        self.membersince_label = pyxbmct.Label('Joined:')
        self.placeControl(self.membersince_label, 4, 1)
        # Membersince text box
        self.membersince_field = pyxbmct.TextBox()
        self.placeControl(self.membersince_field, 4, 2, columnspan=2)

        # Cancel button
        self.cancel_button = pyxbmct.Button('Exit')
        self.placeControl(self.cancel_button, 5, 1)
        # Cancel button closes window

        # Switch button
        self.switch_button = pyxbmct.Button('Switch User')
        self.placeControl(self.switch_button, 5, 2, columnspan=2)

        # Signout button
        self.signout_button = pyxbmct.Button('Sign out')
        self.placeControl(self.signout_button, 5, 4)

        # Submit button to get token
        self.connect(self.cancel_button, self.close)
        self.connect(self.switch_button, lambda: self.switch())
        self.connect(self.signout_button, lambda: self.signout())

    def switch(self):
        xbmc.executebuiltin('XBMC.RunScript(plugin.video.plexbmc, switchuser)')
        self.close()

    def signout(self):
        xbmc.executebuiltin('XBMC.RunScript(plugin.video.plexbmc, signout)')
        if not self.plex_network.is_myplex_signedin():
            self.close()

    def set_navigation(self):
        """Set up keyboard/remote navigation between controls."""
        self.cancel_button.setNavigation(self.switch_button, self.signout_button, self.signout_button, self.switch_button)
        self.switch_button.setNavigation(self.signout_button, self.cancel_button, self.cancel_button, self.signout_button)
        self.signout_button.setNavigation(self.cancel_button, self.switch_button, self.switch_button, self.cancel_button)
