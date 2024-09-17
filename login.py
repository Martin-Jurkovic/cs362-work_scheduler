import tkinter
from tkinter import messagebox
class User:
    def __init__(self, username, password):
        self.username = username
        self.password = password  # maybe make hashed password?
        #store other data related to user here?
    def check_password(self, password):
        return self.password == password  # Replace with hashed password check in a real app

# Create some user objects and store them in a dictionary for easy access
users = {
    'user1': User('user1', 'password123'),
    'user2': User('user2', 'mypassword'),
    'admin': User('admin', 'adminpass')
}

def verify_login(username, password):
    '''Verify the user's credentials and return the user object if successful.'''
    user = users.get(username)  # Get the user object from the dictionary
    if user and user.check_password(password):
        return user
    return None

users = {

}

def userExists(ID, password):
    if [ID, password] in users:
        return True
    return False
def createAccount(ID, password):
    if ID in users:
        print("ID already exists")
    users.append([ID, password])
    
def create_user(users):
    '''Prompts for a new username and password, creates a new User object, and adds it to the users dictionary.'''
    username = input("Enter a new username: ")
    
    # Check if the username already exists
    if username in users:
        print("This username is already taken. Please choose a different username.")
        return None

    password = input("Enter a new password: ")

    # Create a new User object and add it to the dictionary
    new_user = User(username, password)
    users[username] = new_user

    print(f"User '{username}' created successfully!")
    return new_user


    
