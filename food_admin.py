
from xmlrpc import client
proxy =client.ServerProxy("http://localhost:5000/api")


while True:
    print("\nChoose an option:")
    print("1. Create Restaurant")
    print("2. List Restaurants")
    print("3. Update Menu")
    print("4. Show Evaluations")
    print("q. Quit")
    
    choice = input("Enter your choice: ")
    
    if choice == 'q':
        break
    elif choice == '1':
        name, reservations, menu, rating = input("Enter the name, reservations, menu, and rating (separated by spaces): ").split()
        print(proxy.add_restaurant((name, int(reservations), menu, int(rating))))
    elif choice == '2':
        print(proxy.list_all_restaurants())
    elif choice == '3':
        restaurant_id = input("Enter the restaurant ID to update the menu: ")
        new_menu = input("Enter the new menu: ")
        print(proxy.update_menu(int(restaurant_id), new_menu))
    elif choice == '4':
        print(proxy.show_ratings())
    else:
        print("Invalid choice. Please try again.")


   