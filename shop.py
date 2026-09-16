from entities import INGREDIENTS

# Simple way to clear the screen
def clear_screen():
    print("\n" * 100)

# Shop purchase function. Returns True if payment succeeded.
def buy(player, sounds, cost, success_msg, success_sound, fail_msg):
    if player.gold < cost:
        clear_screen()
        print(fail_msg)
        sounds["shop_broke"].play()
        return False
    player.gold -= cost
    print(success_msg)
    clear_screen()
    sounds[success_sound].play()
    return True

# Shop function for interface and such.
def shop(player, sounds):
    shop_inv = list(INGREDIENTS)

    while True:
        print("\n" + "~"*40)
        print("=== THE MARKET ===")
        print("~"*40)
        print(f"Current Gold: {player.gold}")
        print("Available Ingredients:")
        for i in range(6):
            item = shop_inv[i]
            print(f"{i + 1}. {item} - {INGREDIENTS[item]} Gold (In Stock: {player.pantry[item]})")
        print("7. Restock All Ingredients (+2 to each) - 50 Gold")
        print("8. Back to Tavern Hub")
        # Input validation for shop selection.
        raw_choice = input("Select item to buy: ")
        if raw_choice.isdigit():
            choice = int(raw_choice) - 1
        else:
            choice = -1
        # An invalid selection will just loop back to the shop menu.
        if not 0 <= choice <= 7:
            clear_screen()
            print("Invalid selection.")
        elif choice == 7:
            break
        elif choice == 6:
            if buy(player, sounds, 50,
                   "🎉 Bulk order delivered! All pantry ingredients increased by 2.",
                   "shop_restock", "❌ Not enough gold for a bulk restock!"):
                for item in INGREDIENTS:
                    player.pantry[item] += 2
        else:
            item_name = shop_inv[choice]
            if buy(player, sounds, INGREDIENTS[item_name],
                   f"✅ Purchased 1x {item_name}!",
                   "purchase", "❌ Not enough gold for this purchase!"):
                player.pantry[item_name] += 1
