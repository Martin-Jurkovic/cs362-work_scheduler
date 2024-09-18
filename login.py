
from flask import Flask
import tkinter
from tkinter import messagebox
class User:
    def __init__(self, username, password):
        self.username = username
        self.password = password  # In a real application, store a hashed password
        self.data = {}  # Dictionary to store user-specific data

    def check_password(self, password):
        return self.password == password  # Replace with hashed password check in a real app

# Dictionary to store user objects
users = {
    'user1': User('user1', 'password123'),
    'user2': User('user2', 'mypassword'),
    'admin': User('admin', 'adminpass')
}

def create_user(username, password, users=users):
    '''Creates a new User object and adds it to the users dictionary.'''
    # Check if the username already exists
    if username in users:
        return None

    # Create a new User object and add it to the dictionary
    new_user = User(username, password)
    users[username] = new_user

    return new_user

def verify_login(username, password):
    '''Verify the user's credentials and return the user object if successful.'''
    user = users.get(username)  # Get the user object from the dictionary
    if user and user.check_password(password):
        return user
    return None
