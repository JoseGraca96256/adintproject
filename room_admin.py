from xmlrpc import client
proxy =client.ServerProxy("http://localhost:5001/api")


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
        name, capacity, schedule = input("Enter the name, capacity, and schedule (separated by spaces): ").split()
        print(proxy.add_room((name, int(capacity), schedule)))
    elif choice == '2':
        print(proxy.list_all_rooms())
    elif choice == '3':
        room_id = input("Enter the room ID to update the schedule: ")
        new_schedule = input("Enter the new schedule: ")
        print(proxy.update_schedule(int(room_id), new_schedule))
    else:
        print("Invalid choice. Please try again.")
