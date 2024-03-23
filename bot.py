import discord
from discord import app_commands, Interaction, Color
from typing import List
import os
import json
import requests

BOT_TOKEN = os.getenv(BOT_TOKEN)
SERVER_ID = os.getenv(CHANNEL_ID)

intents = discord.Intents.all()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
item_list = {}


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

# NOTE: The json will need to be manually updated every patch cycle that has a
# new item. This can be found in the universalis api.
def parse_items_json():
    with open("items.json", encoding="UTF-8") as file:
        items = json.load(file)
        for item in items:
            item_list[items[item]["en"]] = str(item)


@tree.command(name="order", description="Order an item from Rem.", guild=discord.Object(SERVER_ID))
@app_commands.describe(item="The item you want to buy")
@app_commands.describe(quantity="The quantity of the item you want to buy")
async def order(interaction: Interaction, item: str, quantity: int):
    orders = read_from_file("orders.txt")
    order = {
        "order": item,
        "quantity": quantity,
        "customer": interaction.user.global_name,
        "customer_id": interaction.user.id,
        "discord_name": interaction.user.name,
    }
    orders.append(order)

    if (str(interaction.user) == "bigpp"): # easter egg for boffa
        await interaction.response.send_message(f"Arigatogozaimasu {interaction.user.global_name} senpai! I will ping you when he's done cooking desu~")
    else:
        await interaction.response.send_message("Order received! I'll send this over to Rem and I will ping you when he's done. Thank you for your patronage!")
    write_to_file("orders.txt", orders)


@order.autocomplete("item")
async def item_autocomplete(interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
    data = []
    for item in item_list.keys():
        if current.lower() in item.lower():
            data.append(app_commands.Choice(name=item, value=item))
    return data
    

@tree.command(name="show_orders", description="Show all currently open orders", guild=discord.Object(SERVER_ID))
async def show_orders(interaction: Interaction): 
    embed=discord.Embed(
        title="Current Orders",
        description="Here are the currently open orders:",
        color=Color.blue()
    )

    orders = read_from_file("orders.txt")
    if len(orders) == 0:
        embed.add_field(name="", value="There are currently no orders.")

    counter = 0
    for order in orders:
        val = f'\#{counter}: {order["order"]} \({order["quantity"]}\) ordered by {order["customer"]}'
        embed.add_field(name="", value=val, inline=False)
        counter += 1

    await interaction.response.send_message(embed=embed)


@tree.command(name="complete_order", description="Complete an order", guild=discord.Object(SERVER_ID))
@app_commands.describe(order_num="Order number to complete")
async def complete_order(interaction: Interaction, order_num: int):
    unclaimed_orders = read_from_file("unclaimed.txt")
    if interaction.user.name != "remengis":
        await interaction.response.send_message("Hmmm... You're not Rem... Who are you? Sorry, you can't use this command!")
        return

    orders = read_from_file("orders.txt")
    if order_num >= len(orders):
        await interaction.response.send_message("This order doesn't exist. Try again.")
        return

    order = orders[order_num]
    del orders[order_num]

    unclaimed_orders.append(order)
    write_to_file("orders.txt", orders)
    write_to_file("unclaimed.txt", unclaimed_orders)

    await interaction.response.send_message(f'<@{order["customer_id"]}> Ding! Your order is ready! Please make sure to use `/claim` when receiving your product from Rem!')


@tree.command(name="unclaimed_orders", description="Show your unclaimed orders", guild=discord.Object(SERVER_ID))
async def show_unclaimed_orders(interaction: Interaction):
    unclaimed_orders = []
    all_unclaimed_orders = read_from_file("unclaimed.txt")

    embed=discord.Embed(
        title="Unclaimed Orders",
        description="Here are your unclaimed orders:",
        color=Color.red()
    )

    if len(all_unclaimed_orders) == 0:
        embed.add_field(name="", value="There are currently no unclaimed orders.")

    if interaction.user.name != "remengis":
        unclaimed_orders = [unclaimed for unclaimed in all_unclaimed_orders if unclaimed["discord_name"] == interaction.user.name]
        counter = 0
        for order in unclaimed_orders:
            val = f'\#{counter}: {order["order"]} \({order["quantity"]}\)'
            counter += 1
            embed.add_field(name="", value=val, inline=False)
    else:
        counter = 0
        for order in all_unclaimed_orders:
            val = f'\#{counter}: {order["order"]} \({order["quantity"]}\) ordered by {order["customer"]}'
            counter += 1
            embed.add_field(name="", value=val, inline=False)

    await interaction.response.send_message(embed=embed)


@tree.command(name="claim_all_orders", description="Claim all of your completed orders", guild=discord.Object(SERVER_ID))
async def claim_all_orders(interaction: Interaction):
    claimed_orders = []
    all_unclaimed_orders = read_from_file("unclaimed.txt")
    claimed_orders = [unclaimed for unclaimed in all_unclaimed_orders if unclaimed["discord_name"] == interaction.user.name]

    if len(all_unclaimed_orders) != 0 and interaction.user.name == "remengis":
        write_to_file("unclaimed.txt", [])
        await interaction.response.send_message("Cleared unclaimed orders.")
        return

    if len(claimed_orders) == 0:
        await interaction.response.send_message("You currently don't have any completed orders to claim.")
        return

    unclaimed_orders = filter(lambda order: order not in claimed_orders, all_unclaimed_orders)
    write_to_file("unclaimed.txt", unclaimed_orders)
    await interaction.response.send_message("All orders claimed. Thank you for using Rem Uber Eats! We look forward to serving you again soon!")


@tree.command(name="claim_order", description="Claim one order", guild=discord.Object(SERVER_ID))
@app_commands.describe(order_num="The order you want to claim")
async def claim_order(interaction: Interaction, order_num: int):
    all_unclaimed_orders = read_from_file("unclaimed.txt")

    if len(all_unclaimed_orders) == 0:
        await interaction.response.send_message("You currently don't have any completed orders to claim.")
        return
    elif order_num >= len(all_unclaimed_orders):
        await interaction.response.send_message("Invalid order number. Verify that you used the correct number.")
        return

    order = all_unclaimed_orders[order_num]
    del all_unclaimed_orders[order_num]
    write_to_file("unclaimed.txt", all_unclaimed_orders)

    await interaction.response.send_message(f'<@{order["customer_id"]}> Order claimed. Thank you for using Rem Uber Eats! We look forward to serving you again soon!')


@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=SERVER_ID))
    parse_items_json()
    print("Ready!")


client.run(BOT_TOKEN)

#TODO: have bot send dm to self for each order
#TODO: have an option for someone to edit their order
