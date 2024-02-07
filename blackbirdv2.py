import aiohttp
import asyncio
import requests
from dotenv import load_dotenv
import hashlib
import os
import json

load_dotenv()
listURL = os.getenv("LIST_URL")
listFileName = os.getenv("LIST_FILENAME")


def doSyncRequest(method, url):
    response = requests.request(method=method, url=url)
    parsedData = None

    try:
        parsedData = response.json()
    except:
        pass
    return response, parsedData


def downloadList():
    print("[!] Downloading WhatsMyName list")
    response, parsedData = doSyncRequest("GET", listURL)
    with open(listFileName, "w", encoding="utf-8") as f:
        json.dump(parsedData, f, indent=4)


def hashJSON(jsonData):
    dumpJson = json.dumps(jsonData, sort_keys=True)
    jsonHash = hashlib.md5(dumpJson.encode("utf-8")).hexdigest()
    return jsonHash


def readList():
    f = open(listFileName)
    data = json.load(f)
    return data


def checkUpdates():
    if os.path.isfile(listFileName):
        print("[-] Checking for updates...")
        data = readList()
        currentListHash = hashJSON(data)
        response, data = doSyncRequest("GET", listURL)
        remoteListHash = hashJSON(data)
        if currentListHash != remoteListHash:
            print("[!] Updating...")
            downloadList()
        else:
            print("[+] List is up to date")
    else:
        downloadList()


if __name__ == "__main__":
    checkUpdates()
