import discord
from discord.ext import tasks, commands
from discord.ui import Button, View, Modal, TextInput
import sqlite3
import logging
from main import LIVE_STOCK_CHANNEL_ID  # Import the config value from main

DATABASE = 'store.db'

class LiveStock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.live_stock.start()

    def db_connect(self):
        return sqlite3.connect(DATABASE)

    @tasks.loop(minutes=1)
    async def live_stock(self):
        channel = self.bot.get_channel(LIVE_STOCK_CHANNEL_ID)
        if not channel:
            logging.error('Live stock channel not found')
            return

        conn = self.db_connect()
        cursor = conn.cursor()
        cursor.execute("SELECT name, stock FROM products")
        products = cursor.fetchall()
        conn.close()

        if products:
            stock_list = '\n'.join([f"{name}: {stock} in stock" for name, stock in products])
            message = f"Current stock:\n{stock_list}"
        else:
            message = "No products available."

        async for msg in channel.history(limit=10):
            if msg.author == self.bot.user:
                await msg.delete()

        # Buat tombol
        button_balance = Button(label="Check Balance", style=discord.ButtonStyle.secondary)
        button_buy = Button(label="Buy", style=discord.ButtonStyle.primary)
        button_set_growid = Button(label="Set GrowID", style=discord.ButtonStyle.success)

        async def button_balance_callback(interaction):
            conn = self.db_connect()
            cursor = conn.cursor()
            cursor.execute("SELECT growid FROM user_growid WHERE user_id = ?", (interaction.user.id,))
            growid = cursor.fetchone()
            if growid:
                cursor.execute("SELECT balance FROM users WHERE growid = ?", (growid[0],))
                user_balance = cursor.fetchone()
                conn.close()
                if user_balance:
                    await interaction.response.send_message(f"Your balance is: {user_balance[0]}")
                else:
                    await interaction.response.send_message("No balance found for your GrowID.")
            else:
                conn.close()
                await interaction.response.send_message("No GrowID found for your account.")

        async def button_buy_callback(interaction):
            modal = BuyModal(self.bot)
            await interaction.response.send_modal(modal)

        async def button_set_growid_callback(interaction):
            modal = SetGrowIDModal(self.bot)
            await interaction.response.send_modal(modal)

        button_balance.callback = button_balance_callback
        button_buy.callback = button_buy_callback
        button_set_growid.callback = button_set_growid_callback
        view = View()
        view.add_item(button_balance)
        view.add_item(button_buy)
        view.add_item(button_set_growid)

        await channel.send(message, view=view)

    @live_stock.before_loop
    async def before_live_stock(self):
        await self.bot.wait_until_ready()

class SetGrowIDModal(Modal):
    def __init__(self, bot):
        super().__init__(title="Set GrowID")
        self.bot = bot
        self.add_item(TextInput(label="GrowID", placeholder="Enter your GrowID here"))

    async def on_submit(self, interaction):
        growid = self.children[0].value
        try:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO user_growid (user_id, growid) VALUES (?, ?)", (interaction.user.id, growid))
            conn.commit()
            conn.close()
            await interaction.response.send_message(f"GrowID {growid} has been set for user {interaction.user.name}.", ephemeral=True)
        except Exception as e:
            logging.error(f'Error in setgrowid: {e}')
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

class BuyModal(Modal):
    def __init__(self, bot):
        super().__init__(title="Buy Product")
        self.bot = bot
        self.add_item(TextInput(label="Product", placeholder="Enter the product name"))
        self.add_item(TextInput(label="Quantity", placeholder="Enter the quantity", style=discord.TextStyle.short))

    async def on_submit(self, interaction):
        product = self.children[0].value
        quantity = int(self.children[1].value)
        try:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()

            cursor.execute("SELECT stock, price FROM products WHERE name = ?", (product,))
            product_info = cursor.fetchone()
            if not product_info:
                await interaction.response.send_message("Product not found.", ephemeral=True)
                conn.close()
                return

            stock, price = product_info
            total_price = price * quantity

            cursor.execute("SELECT growid FROM user_growid WHERE user_id = ?", (interaction.user.id,))
            growid = cursor.fetchone()
            if growid:
                cursor.execute("SELECT balance FROM users WHERE growid = ?", (growid[0],))
                user_balance = cursor.fetchone()
                if not user_balance or user_balance[0] < total_price:
                    await interaction.response.send_message("Insufficient balance.", ephemeral=True)
                    conn.close()
                    return

                if stock < quantity:
                    await interaction.response.send_message("Not enough stock.", ephemeral=True)
                    conn.close()
                    return

                cursor.execute("UPDATE products SET stock = stock - ? WHERE name = ?", (quantity, product))
                cursor.execute("UPDATE users SET balance = balance - ? WHERE growid = ?", (total_price, growid[0]))
                cursor.execute("INSERT OR REPLACE INTO purchases (user_id, product, quantity) VALUES (?, ?, COALESCE((SELECT quantity FROM purchases WHERE user_id = ? AND product = ?), 0) + ?)", 
                               (interaction.user.id, product, interaction.user.id, product, quantity))
                conn.commit()
                conn.close()
                await interaction.response.send_message(f"Successfully purchased {quantity} {product}(s) for {total_price} units.", ephemeral=True)
            else:
                conn.close()
                await interaction.response.send_message("No GrowID found for your account.", ephemeral=True)
        except Exception as e:
            logging.error(f'Error in buy: {e}')
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(LiveStock(bot))
