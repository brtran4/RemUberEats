import discord
from dotenv import load_dotenv
from datetime import datetime, timedelta
from discord import app_commands, Interaction, Color
from typing import List, Optional
import os
import json
import asyncio

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN") or ""
SERVER_ID: str = os.getenv("SERVER_ID") or ""
ABSENCE_CHANNEL_ID: str = os.getenv("ABSENCE_CHANNEL_ID") or "1261489115841564682"

if not BOT_TOKEN:
    raise ValueError("Bot token not supplied")
if not SERVER_ID:
    raise ValueError("Server id not supplied")

intents = discord.Intents.all()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
item_list = {}

ABSENCES_FILE = "absences.txt"
ORDERS_FILE = "orders.txt"
UNCLAIMED_FILE = "unclaimed.txt"
ITEMS_FILE = "items.json"


def write_to_file(file, orders):
    with open(file, "w") as file:
        for order in orders:
            file.write(json.dumps(order) + "\n")


def read_from_file(input_file):
    orders = []
    try:
        with open(input_file, "r") as file:
            for order in file:
                orders.append(json.loads(order))
    except:
        with open(input_file, "w") as file:
            file.write("")
    return orders


def read_absences():
    absences = []
    try:
        with open(ABSENCES_FILE, "r") as file:
            for line in file:
                line = line.strip()
                if line:
                    parts = line.split("|")
                    if len(parts) >= 2:
                        absence = {"date": parts[0].strip(), "user": parts[1].strip()}
                        if len(parts) >= 3 and parts[2].strip():
                            absence["user_id"] = parts[2].strip()
                        absences.append(absence)
    except FileNotFoundError:
        pass
    return absences


def filter_past_absences():
    absences = read_absences()
    today = datetime.now().date()
    future_absences = []
    for absence in absences:
        absence_date = datetime.strptime(absence["date"], "%m/%d/%Y").date()
        if absence_date >= today:
            future_absences.append(absence)
    if len(future_absences) != len(absences):
        with open(ABSENCES_FILE, "w") as file:
            for absence in future_absences:
                file.write(f"{absence['date']} | {absence['user']}\n")
    return future_absences


def get_todays_absences():
    absences = read_absences()
    today = datetime.now().strftime("%m/%d/%Y")
    todays_absences = []
    for absence in absences:
        if absence["date"] == today:
            user_id = absence.get("user_id", "")
            todays_absences.append(user_id)
    return todays_absences


def add_absence(date_str: str, user: str, user_id: int):
    absences = read_absences()
    absences.append({"date": date_str, "user": user, "user_id": str(user_id)})
    with open(ABSENCES_FILE, "w") as file:
        for absence in absences:
            file.write(
                f"{absence['date']} | {absence['user']} | {absence.get('user_id', '')}\n"
            )


# NOTE: The json will need to be manually updated every patch cycle that has a
# new item. This can be found in the xivapi API.
def parse_items_json():
    with open(ITEMS_FILE, encoding="UTF-8") as file:
        items = json.load(file)
        for item in items:
            item_list[items[item]["en"]] = str(item)


def refresh_items():
    item_list.clear()
    parse_items_json()


@tree.command(
    name="refresh_items",
    description="Refresh the item list from items.json",
    guild=discord.Object(id=int(SERVER_ID)),
)
async def refresh_items_command(interaction: Interaction):
    if interaction.user.name != "remengis":
        await interaction.response.send_message(
            "Hmmm... You're not Rem... Who are you? Sorry, you can't use this command!",
            ephemeral=True,
        )
        return

    refresh_items()
    await interaction.response.send_message(
        "Item list refreshed!",
        ephemeral=True,
    )


@tree.command(
    name="order", description="Order an item from Rem.", guild=discord.Object(SERVER_ID)
)
@app_commands.describe(item="The item you want to buy")
@app_commands.describe(quantity="The quantity of the item you want to buy")
async def order(interaction: Interaction, item: str, quantity: int):
    orders = read_from_file(ORDERS_FILE)
    order = {
        "order": item,
        "quantity": quantity,
        "customer": interaction.user.global_name,
        "customer_id": interaction.user.id,
        "discord_name": interaction.user.name,
    }
    orders.append(order)

    await interaction.response.send_message(
        "Order received! I'll send this over to Rem and I will ping you when he's done. Thank you for your patronage!",
        ephemeral=True,
    )
    write_to_file(ORDERS_FILE, orders)

    await send_dm(order)


@order.autocomplete("item")
async def item_autocomplete(
    interaction: Interaction, current: str
) -> List[app_commands.Choice[str]]:
    data = []
    for item in item_list.keys():
        if current.lower() in item.lower():
            data.append(app_commands.Choice(name=item, value=item))
    return data


@tree.command(
    name="show_orders",
    description="Show all currently open orders",
    guild=discord.Object(SERVER_ID),
)
async def show_orders(interaction: Interaction):
    embed = discord.Embed(
        title="Current Orders",
        description="Here are the currently open orders:",
        color=Color.blue(),
    )

    orders = read_from_file(ORDERS_FILE)
    if len(orders) == 0:
        embed.add_field(name="", value="There are currently no orders.")

    counter = 0
    for order in orders:
        val = f"#{counter}: {order['order']} ({order['quantity']}) ordered by {order['customer']}"
        embed.add_field(name="", value=val, inline=False)
        counter += 1

    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(
    name="complete_order",
    description="Complete an order",
    guild=discord.Object(SERVER_ID),
)
@app_commands.describe(order_num="Order number to complete")
async def complete_order(interaction: Interaction, order_num: int):
    unclaimed_orders = read_from_file(UNCLAIMED_FILE)
    if interaction.user.name != "remengis":
        await interaction.response.send_message(
            "Hmmm... You're not Rem... Who are you? Sorry, you can't use this command!",
            ephemeral=True,
        )
        return

    orders = read_from_file(ORDERS_FILE)
    if order_num >= len(orders):
        await interaction.response.send_message(
            "This order doesn't exist. Try again.", ephemeral=True
        )
        return

    order = orders[order_num]
    del orders[order_num]

    unclaimed_orders.append(order)
    write_to_file(ORDERS_FILE, orders)
    write_to_file(UNCLAIMED_FILE, unclaimed_orders)

    await interaction.response.send_message(
        f"<@{order['customer_id']}> Ding! Your order is ready!"
    )


@tree.command(
    name="unclaimed_orders",
    description="Show your unclaimed orders",
    guild=discord.Object(SERVER_ID),
)
async def show_unclaimed_orders(interaction: Interaction):
    unclaimed_orders = []
    all_unclaimed_orders = read_from_file(UNCLAIMED_FILE)

    embed = discord.Embed(
        title="Unclaimed Orders",
        description="Here are your unclaimed orders:",
        color=Color.red(),
    )

    if len(all_unclaimed_orders) == 0:
        embed.add_field(name="", value="There are currently no unclaimed orders.")

    if interaction.user.name != "remengis":
        unclaimed_orders = [
            unclaimed
            for unclaimed in all_unclaimed_orders
            if unclaimed["discord_name"] == interaction.user.name
        ]
        counter = 0
        for order in unclaimed_orders:
            val = f"#{counter}: {order['order']} ({order['quantity']})"
            counter += 1
            embed.add_field(name="", value=val, inline=False)
    else:
        counter = 0
        for order in all_unclaimed_orders:
            val = f"#{counter}: {order['order']} ({order['quantity']}) ordered by {order['customer']}"
            counter += 1
            embed.add_field(name="", value=val, inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(
    name="claim_all_orders",
    description="Claim all of your completed orders",
    guild=discord.Object(SERVER_ID),
)
async def claim_all_orders(interaction: Interaction):
    claimed_orders = []
    all_unclaimed_orders = read_from_file(UNCLAIMED_FILE)
    claimed_orders = [
        unclaimed
        for unclaimed in all_unclaimed_orders
        if unclaimed["discord_name"] == interaction.user.name
    ]

    if len(all_unclaimed_orders) != 0 and interaction.user.name == "remengis":
        write_to_file(UNCLAIMED_FILE, [])
        await interaction.response.send_message(
            "Cleared unclaimed orders.", ephemeral=True
        )
        return

    if len(claimed_orders) == 0:
        await interaction.response.send_message(
            "You currently don't have any completed orders to claim."
        )
        return

    unclaimed_orders = filter(
        lambda order: order not in claimed_orders, all_unclaimed_orders
    )
    write_to_file(UNCLAIMED_FILE, unclaimed_orders)
    await interaction.response.send_message(
        "All orders claimed. Thank you for using Rem Uber Eats! We look forward to serving you again soon!"
    )


@tree.command(
    name="claim_order", description="Claim one order", guild=discord.Object(SERVER_ID)
)
@app_commands.describe(order_num="The order you want to claim")
async def claim_order(interaction: Interaction, order_num: int):
    all_unclaimed_orders = read_from_file(UNCLAIMED_FILE)

    if len(all_unclaimed_orders) == 0:
        await interaction.response.send_message(
            "You currently don't have any completed orders to claim."
        )
        return
    elif order_num >= len(all_unclaimed_orders):
        await interaction.response.send_message(
            "Invalid order number. Verify that you used the correct number."
        )
        return

    order = all_unclaimed_orders[order_num]
    del all_unclaimed_orders[order_num]
    write_to_file(UNCLAIMED_FILE, all_unclaimed_orders)

    await interaction.response.send_message(
        f"<@{order['customer_id']}> Order claimed. Thank you for using Rem Uber Eats! We look forward to serving you again soon!"
    )


# send Rem a DM about a new order
async def send_dm(order):
    user = await client.fetch_user(int("104917239962046464"))
    await user.send(
        f"{order['customer']} submitted an order for {order['quantity']} {order['order']}"
    )


@tree.command(
    name="absent",
    description="Submit your absence notice",
    guild=discord.Object(SERVER_ID),
)
@app_commands.describe(date="Date in MM/DD/YYYY format")
async def absent(interaction: Interaction, date: str):
    try:
        parsed_date = datetime.strptime(date, "%m/%d/%Y").date()
        formatted_date = parsed_date.strftime("%m/%d/%Y")
    except ValueError:
        await interaction.response.send_message(
            "Invalid date format. Please use MM/DD/YYYY format.",
            ephemeral=True,
        )
        return

    today = datetime.now().date()
    yesterday = (datetime.now() - timedelta(days=1)).date()

    if parsed_date < yesterday:
        await interaction.response.send_message(
            "Cannot record an absence for a past date.",
            ephemeral=True,
        )
        return

    user_name = interaction.user.global_name or interaction.user.name
    user_id = interaction.user.id
    add_absence(formatted_date, user_name, user_id)

    await interaction.response.send_message(
        f"Absence recorded for {formatted_date} by {user_name}.",
        ephemeral=True,
    )


@tree.command(
    name="view_absences",
    description="View all absences",
    guild=discord.Object(SERVER_ID),
)
async def view_absences(interaction: Interaction):
    absences = filter_past_absences()

    embed = discord.Embed(
        title="Absences",
        description="Here are all recorded absences:",
        color=Color.green(),
    )

    if not absences:
        embed.add_field(name="", value="No absences recorded.")
    else:
        for absence in absences:
            value = f"**Date:** {absence['date']}\n**User:** {absence['user']}"
            embed.add_field(name="", value=value, inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)


@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=int(SERVER_ID)))
    parse_items_json()
    print("Ready!")
    asyncio.create_task(schedule_past_absences_cleanup())


async def schedule_past_absences_cleanup():
    while True:
        now = datetime.now()
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(
            days=1
        )
        seconds_until_midnight = (tomorrow - now).total_seconds()
        await asyncio.sleep(seconds_until_midnight)

        filter_past_absences()
        print("Cleaned up past absences")

        todays_absences = get_todays_absences()
        if todays_absences and ABSENCE_CHANNEL_ID:
            channel = client.get_channel(int(ABSENCE_CHANNEL_ID))
            if channel and isinstance(channel, discord.TextChannel):
                valid_ids = [u for u in todays_absences if u]
                if valid_ids:
                    users_mentions = " ".join(f"<@{u}>" for u in valid_ids)
                    verb = "is" if len(valid_ids) == 1 else "are"
                    await channel.send(
                        f"Attention: {users_mentions} {verb} absent today!"
                    )


if __name__ == "__main__":
    client.run(BOT_TOKEN)

# TODO: have bot send dm to self for each order
# TODO: have an option for someone to edit their order
