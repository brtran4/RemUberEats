import discord
from discord import app_commands, Interaction, Color
import os

BOT_TOKEN = os.getenv(BOT_TOKEN)
SERVER_ID = os.getenv(CHANNEL_ID)

intents = discord.Intents.all()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

orders = []

@tree.command(name="order", description="Order an item from Rem.", guild=discord.Object(SERVER_ID))
@app_commands.describe(item="The item you want to buy")
@app_commands.describe(quantity="The quantity of the item you want to buy")
async def order(interaction: Interaction, item: str, quantity: int):
    order = {
        "order": item,
        "quantity": quantity,
        "customer": interaction.user.global_name,
        "customer_id": interaction.user,
        "discord_name": interaction.user.name,
    }
    orders.append(order)

    if (str(interaction.user) == "bigpp"): # easter egg for boffa
        await interaction.response.send_message(f"Arigatogozaimasu {interaction.user.global_name} senpai! I will ping you when he's done cooking desu~")
    else:
        await interaction.response.send_message("Order received! I'll send this over to Rem and I will ping you when he's done. Thank you for your patronage!")
    


@tree.command(name="show_orders", description="Show all currently open orders", guild=discord.Object(SERVER_ID))
async def show_orders(interaction: Interaction): 
    embed=discord.Embed(
    title="Current Orders",
        description="Here are the currently open orders:",
        color=Color.blue()
    )

    counter = 0
    for order in orders:
        val = f'\#{counter}: {order["order"]} \({order["quantity"]}\) ordered by {order["customer"]}'
        embed.add_field(name="", value=val, inline=False)
        counter += 1
    
    if len(orders) == 0:
        embed.add_field(name="", value="There are currently no orders.")

    await interaction.response.send_message(embed=embed)


@tree.command(name="complete_order", description="Complete an order", guild=discord.Object(SERVER_ID))
@app_commands.describe(order_num="Order number to complete")
async def complete_order(interaction: Interaction, order_num: int):
    if interaction.user.name != "remengis":
        await interaction.response.send_message("Hmmm... You're not Rem... Who are you? Sorry, you can't use this command!")
        return
    
    if order_num >= len(orders):
        await interaction.response.send_message("This order doesn't exist. Try again.")
        return

    order = orders[order_num]
    del orders[order_num]
    await interaction.response.send_message(f'{order["customer_id"].mention} Ding! Your order is ready!')



@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=SERVER_ID))
    print("Ready!")


client.run(BOT_TOKEN)

#TODO: have bot send dm to self for each order
#TODO: have an option for someone to edit their order
