from entities import INGREDIENTS

# Simple way to clear the screen
def clear_screen():
    print("\n" * 100)

# Returns True if the player could pay.
def buy(player, sounds, cost, success_msg, success_sound, fail_msg):
    if player.gold < cost:
        clear_screen()
        print(fail_msg)
        sounds["shop_broke"].play()
        return False
    player.gold -= cost
    clear_screen()
    print(success_msg)
    sounds[success_sound].play()
    return True

# Shop menu loop
def shop(player, sounds):
    shop_inv = list(INGREDIENTS)
    # 0-based; the two options after the ingredients.
    restock_choice = len(shop_inv)
    back_choice = restock_choice + 1

    while True:
        print("\n" + "~"*40)
        print("=== THE MARKET ===")
        print("~"*40)
        print(f"Current Gold: {player.gold}")
        print("Available Ingredients:")
        for i, item in enumerate(shop_inv, start=1):
            print(f"{i}. {item} - {INGREDIENTS[item]} Gold (In Stock: {player.pantry[item]})")
        print(f"{restock_choice + 1}. Restock All Ingredients (+2 to each) - 50 Gold")
        print(f"{back_choice + 1}. Back to Tavern Hub")
        raw_choice = input("Select item to buy: ")
        if raw_choice.isdigit():
            choice = int(raw_choice) - 1
        else:
            choice = -1
        if not 0 <= choice <= back_choice:
            clear_screen()
            print("Invalid selection.")
        elif choice == back_choice:
            break
        elif choice == restock_choice:
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
