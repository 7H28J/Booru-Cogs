import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
from __main__ import send_cmd_help
from urllib import parse
import os
import aiohttp

class Loli:
    def __init__(self, bot):
        self.bot = bot
        self.filters = fileIO("data/loli/filters.json", "load")
        self.settings = fileIO("data/loli/settings.json", "load")

    @commands.command(pass_context=True,no_pm=True)
    async def loli(self, ctx, *text):
        """Retrieves the latest result from Lolibooru"""
        server = ctx.message.server
        if len(text) > 0:
            await fetch_image(self, ctx, randomize=False, tags=text)
        else:
            await send_cmd_help(ctx)

    @commands.command(pass_context=True,no_pm=True)
    async def lolir(self, ctx, *text):
        """Retrieves a random result from Lolibooru"""
        server = ctx.message.server
        await fetch_image(self, ctx, randomize=True, tags=text)

    @commands.group(pass_context=True)
    async def lolifilter(self, ctx):
        """Manages loli filters
           Warning: Can be used to allow NSFW images

           Filters automatically apply tags to each search"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @lolifilter.command(name="add", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _add_lolifilter(self, ctx, filtertag : str):
        """Adds a tag to the server's loli filter list

           Example: !lolifilter add rating:s"""
        server = ctx.message.server
        if server.id not in self.filters:
            self.filters[server.id] = self.filters["default"]
            fileIO("data/loli/filters.json", "save", self.filters)
            self.filters = fileIO("data/loli/filters.json", "load")
        if len(self.filters[server.id]) < int(self.settings["maxfilters"]):
            if filtertag not in self.filters[server.id]:
                self.filters[server.id].append(filtertag)
                fileIO("data/loli/filters.json", "save", self.filters)
                await self.bot.say("Filter '{}' added to the server's loli filter list.".format(filtertag))
            else:
                await self.bot.say("Filter '{}' is already in the server's loli filter list.".format(filtertag))
        else:
            await self.bot.say("This server has exceeded the maximum filters ({}/{}). https://www.youtube.com/watch?v=1MelZ7xaacs".format(len(self.filters[server.id]), self.settings["maxfilters"]))

    @lolifilter.command(name="del", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _del_lolifilter(self, ctx, filtertag : str=""):
        """Deletes a tag from the server's loli filter list

           Without arguments, reverts to the default loli filter list

           Example: !lolifilter del rating:s"""
        server = ctx.message.server
        if len(filtertag) > 0:
            if server.id not in self.filters:
                self.filters[server.id] = self.filters["default"]
                fileIO("data/loli/filters.json", "save", self.filters)
                self.filters = fileIO("data/loli/filters.json", "load")
            if filtertag in self.filters[server.id]:
                self.filters[server.id].remove(filtertag)
                fileIO("data/loli/filters.json", "save", self.filters)
                await self.bot.say("Filter '{}' deleted from the server's loli filter list.".format(filtertag))
            else:
                await self.bot.say("Filter '{}' does not exist in the server's loli filter list.".format(filtertag))
        else:
            if server.id in self.filters:
                del self.filters[server.id]
                fileIO("data/loli/filters.json", "save", self.filters)
                await self.bot.say("Reverted the server to the default loli filter list.")
            else:
                await self.bot.say("Server is already using the default loli filter list.")

    @lolifilter.command(name="list", pass_context=True)
    async def _list_lolifilter(self, ctx):
        """Lists all of the filters currently applied to the current server"""
        server = ctx.message.server
        if server.id in self.filters:
            filterlist = '\n'.join(sorted(self.filters[server.id]))
            targetServer = "{}'s".format(server.name)
        else:
            filterlist = '\n'.join(sorted(self.filters["default"]))
            targetServer = "Default"
        await self.bot.say("{} loli filter list contains:```\n{}```".format(targetServer, filterlist))

    @commands.group(pass_context=True)
    @checks.is_owner()
    async def loliset(self, ctx):
        """Manages loli options"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @loliset.command(pass_context=True,name="verbose")
    @checks.admin_or_permissions(manage_server=True)
    async def _verbose_loliset(self, ctx, toggle : str = "toggle"):
        """Toggles verbose mode"""
        server = ctx.message.server
        if server.id not in self.settings:
            self.settings[server.id] = {"verbose":False}
            fileIO("data/loli/settings.json", "save", self.settings)
            self.settings = fileIO("data/loli/settings.json", "load")
        if toggle.lower() == "on" or toggle.lower() == "true" or toggle.lower() == "enable":
            if not self.settings[server.id]["verbose"]:
                self.settings[server.id]["verbose"] = True
                await self.bot.say("Verbose mode is now enabled.")
            else:
                await self.bot.say("Verbose mode is already enabled.")
        elif toggle.lower() == "off" or toggle.lower() == "false" or toggle.lower() == "disable":
            if self.settings[server.id]["verbose"]:
                self.settings[server.id]["verbose"] = False
                await self.bot.say("Verbose mode is now disabled.")
            else:
                await self.bot.say("Verbose mode is already disabled.")
        else:
            if self.settings[server.id]["verbose"]:
                self.settings[server.id]["verbose"] = False
                await self.bot.say("Verbose mode is now disabled.")
            else:
                self.settings[server.id]["verbose"] = True
                await self.bot.say("Verbose mode is now enabled.")
        fileIO("data/loli/settings.json", "save", self.settings)

    @loliset.command(name="maxfilters")
    async def _maxfilters_loliset(self, maxfilters):
        """Sets the global tag limit for the filter list

           Gives an error when a user tries to add a filter while the server's filter list contains a certain amount of tags"""
        self.settings["maxfilters"] = maxfilters
        fileIO("data/loli/settings.json", "save", self.settings)
        await self.bot.say("Maximum filters allowed per server for loli set to '{}'.".format(maxfilters))

async def fetch_image(self, ctx, randomize, tags):
    server = ctx.message.server
    self.filters = fileIO("data/loli/filters.json", "load")
    self.settings = fileIO("data/loli/settings.json", "load")

    # Initialize verbosity as false
    verbose = False

    # Set verbosity to true if the current server has it set as such
    if server.id in self.settings and self.settings[server.id]["verbose"]:
        verbose = True

    # Initialize base URL
    search = "https://lolibooru.moe/post/index.json?limit=1&tags="
    tagSearch = ""

    # Assign tags to URL
    if tags:
        tagSearch += "{} ".format(" ".join(tags))
    if server.id in self.filters:
        tagSearch += " ".join(self.filters[server.id])
    else:
        tagSearch += " ".join(self.filters["default"])
    if randomize:
        tagSearch += " order:random"
    search += parse.quote_plus(tagSearch)

    # Inform users about image retrieval
    message = await self.bot.say("Fetching loli image...")

    # Fetch and display the image or an error
    try:
        async with aiohttp.get(search) as r:
            website = await r.json()
        if website != []:
            imageURL = website[0].get("file_url").replace(' ', '+')
            if verbose:
                # Check for the rating and set an appropriate color
                tagList = website[0].get('tags')
                rating = website[0].get('rating')
                if rating == "s":
                    rating = "safe"
                    ratingColor = "00FF00"
                elif rating == "q":
                    rating = "questionable"
                    ratingColor = "FF9900"
                elif rating == "e":
                    rating = "explicit"
                    ratingColor = "FF0000"
                if not rating:
                    rating = "unknown"
                    ratingColor = "FFFFFF"

                # Sets the URL to be linked
                link = "https://lolibooru.moe/post/show/{}".format(website[0].get('id'))
                
                # Initialize verbose embed
                output = discord.Embed(description=link, colour=discord.Colour(value=int(ratingColor, 16)))

                # Sets the thumbnail and adds the rating and tag fields to the embed
                output.add_field(name="Rating", value=rating)
                output.add_field(name="Tags", value=tagList.replace('_', '\_'))
                output.set_thumbnail(url=imageURL)

                # Edits the pending message with the results
                return await self.bot.edit_message(message, "Image found.", embed=output)
            else:
                # Edits the pending message with the result
                return await self.bot.edit_message(message, imageURL)
        else:
            return await self.bot.edit_message(message, "Your search terms gave no results.")
    except:
        return await self.bot.edit_message(message, "Error.")

def check_folder():
    if not os.path.exists("data/loli"):
        print ("Creating data/loli folder...")
        os.makedirs("data/loli")

def check_files():
    filters = {"default":["rating:safe"]}
    settings = {"maxfilters":"50"}

    if not fileIO("data/loli/filters.json", "check"):
        print("Creating default loli filters.json...")
        fileIO("data/loli/filters.json", "save", filters)
    else:
        filterlist = fileIO("data/loli/filters.json", "load")
        if "default" not in filterlist:
            filterlist["default"] = filters["default"]
            print("Adding default loli filters...")
            fileIO("data/loli/filters.json", "save", filterlist)
    if not fileIO("data/loli/settings.json", "check"):
        print("Creating default loli settings.json...")
        fileIO("data/loli/settings.json", "save", settings)

def setup(bot):
    check_folder()
    check_files()
    bot.add_cog(Loli(bot))
