import config
import os
from pathlib import Path
from rich.markup import escape
import time
import aiohttp
import asyncio
import sys

from modules.utils.filter import filterFoundAccounts, applyFilters
from modules.utils.parse import extractMetadata
from modules.utils.http_client import do_async_request
from modules.whatsmyname.list_operations import readList
from src.modules.utils.input import processInput
from modules.utils.log import logError
from modules.export.csv import saveToCsv
from modules.export.pdf import saveToPdf
from src.modules.export.dump import dumpContent
from modules.export.file_operations import createSaveDirectory

# Verify account existence based on list args
async def checkSite(site, method, url, session, data=None, headers=None):
    returnData = {"name": site["name"], "url": url, "status": "NONE", "metadata": []}
    response = await do_async_request(method, url, session, data, headers)
    if response == None:
        returnData["status"] = "ERROR"
        return returnData
    try:
        if response:
            if (site["e_string"] in response["content"]) and (
                site["e_code"] == response["status_code"]
            ):
                if (site["m_string"] not in response["content"]) and (
                    site["m_code"] != response["status_code"]
                ):
                    returnData["status"] = "FOUND"
                    config.console.print(
                        f"  ✔️  \[[cyan1]{site['name']}[/cyan1]] [bright_white]{response['url']}[/bright_white]"
                    )
                    if (site["metadata"]):
                        metadataItem = extractMetadata(site["metadata"], response)
                        returnData["metadata"].append(metadataItem)
                    # Save response content to a .HTML file
                    if config.dump:
                        path = os.path.join(config.saveDirectory, f"dump_{config.email}")

                        result = dumpContent(path, site, response)
                        if result == True and config.verbose:
                            config.console.print(
                                f"      💾  Saved HTML data from found account"
                            )
            else:
                returnData["status"] = "NOT-FOUND"
                if config.verbose:
                    config.console.print(
                        f"  ❌ [[blue]{site['name']}[/blue]] [bright_white]{response['url']}[/bright_white]"
                    )
            return returnData
    except Exception as e:
        logError(e, f"Coudn't check {site['name']} {url}")
        return returnData

# Control survey on list sites
async def fetchResults(email):
    data = readList("email")

    async with aiohttp.ClientSession() as session:
        tasks = []

        for site in config.email_sites:
            if site["input_operation"]:
                email = processInput(config.email, site["input_operation"])
            else:
                email = config.email
            url = site["uri_check"].replace("{account}", email)
            data = site["data"].replace("{account}", email) if site["data"] else None
            headers = site["headers"] if site["headers"] else None
            tasks.append(
                checkSite(
                    site=site,
                    method=site["method"],
                    url=url,
                    session=session,
                    data=data,
                    headers=headers
                )
            )
        tasksResults = await asyncio.gather(*tasks, return_exceptions=True)
        results = {
            "results": tasksResults,
            "email": email
        }
    return results

# Start email check and presents results to user
def verifyEmail(email):
    
    data = readList("email")
    sitesToSearch = data["sites"]
    config.email_sites = applyFilters(sitesToSearch)

    if config.dump or config.csv or config.pdf:
        createSaveDirectory()

    config.console.print(
        f':play_button: Enumerating accounts with email "[cyan1]{email}[/cyan1]"'
    )
    start_time = time.time()
    results = asyncio.run(fetchResults(email))
    end_time = time.time()
    
    config.console.print(
        f":chequered_flag: Check completed in {round(end_time - start_time, 1)} seconds ({len(results['results'])} sites)"
    )

    if config.dump:
        config.console.print(f"💾  Dump content saved to '[cyan1]{config.email}_{config.dateRaw}_blackbird/dump_{config.email}[/cyan1]'")
    
    # Filter results to only found accounts
    foundAccounts = list(filter(filterFoundAccounts, results["results"]))
    
    if (len(foundAccounts) > 0):

        if config.csv:
            saveToCsv(results["username"], config.dateRaw, foundAccounts)

        if config.pdf:
            saveToPdf(results["username"], config.datePretty, config.dateRaw, foundAccounts)
    else:
        config.console.print("⭕ No accounts were found for the given username")