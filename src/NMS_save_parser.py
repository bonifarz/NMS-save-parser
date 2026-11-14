# the functions of this module use standard libraries ...
import os
import json
import csv
from urllib.request import urlopen
from datetime import datetime, timedelta
import math as np
# ... except for lz4, as required for the nmssavetool's decompress function
from nmssavetool import readFile, writeFile, decompress

class save_parser_class:
    """Wrap up the module in a class for ease of further development."""

    def __init__(self, logger):
        """When a new instance is created, take over the passed logger and load the mapping data."""
        self.log = logger
        self.log.info(100*"-")
        self.log.info("loading definitions... to force a new download, just delete a file from ./download/")
        self.get_readme()
        self.get_nms_tables()
        self.get_mapping()

    def parse_saves_from_io(self):
        """Process all hg files in the ./io/ folder."""
        self.log.info("Checking for .hg files in the ./io/ folder ...")
        for filename in os.listdir("./io/"):
            if filename.endswith(".hg"):
                self.fn = "io/"+filename
                self.parse_save()
        self.log.info("All done.\n") 

    def parse_save(self):
        """Process one hg file at a time."""
        self.log.info(f"decompressing and parsing the file {self.fn}")
        # once you have seen the result, you can comment out the below test line:
        writeFile(self.fn+".obfuscated.json", decompress(readFile(self.fn)))
        # apply the name mapping to the decompressed save data:
        try:
            self.save = self.apply_mapping(decompress(readFile(self.fn)))
        except:
            self.log.info("  ... file skipped, not valid save for our mappings.")
            return
        self.write_save_json()
        # define the prefixes for all following output files below:
        self.fn += "."+self.save["CommonStateData"]["SaveName"]
        self.fn += "."+str(self.save["CommonStateData"]["TotalPlayTime"])
        # here you can select (and add your own) data parsing steps as needed:
        self.parse_inventory()
        self.parse_bases()
        self.parse_discoveries()
        self.parse_varia()

    def write_save_json(self):
        """Store the save data in a long json format."""
        fno = self.fn+".long.json"
        f = open(fno, "w", encoding="ansi")
        f.write(json.dumps(self.save, indent=2))
        f.close
        self.log.info(f"  ... done, full json dump written")
        
    def parse_bases(self):
        """Extract info about bases from one save into some tsv files."""
        tsvreport = open(self.fn+".bases.tsv", 'w', newline='', encoding='utf-8')
        report = csv.writer(tsvreport, delimiter='\t') #  delimiter='\t')
        report.writerow(["GalacticAddress", "RId", f"{"Glpyhs":14}", f"{"LastUpdateTimestamp":22}", f"{"Objects":5}",
                         f"{"PosR":>9}", f"{"PosNS":>7}", f"{"PosEW":>7}", f"{"BaseType":18}", "BaseName"])

        tsvdetail = open(self.fn+".baseparts.tsv", 'w', newline='', encoding='utf-8')
        detail = csv.writer(tsvdetail, delimiter='\t')
        detail.writerow([f"{"partId":20}", f"{"partName":30}", f"{"xPos":>10}", f"{"yPos":>10}", f"{"zPos":>10}", 
                         f"{"Timestamp":>22}", "BaseName"])

        bases = self.save["BaseContext"]["PlayerStateData"]["PersistentPlayerBases"]
        basecount = 0
        totalparts = 0
        for k in bases:
            basecount += 1
            parts = len(k["Objects"]) 
            totalparts += parts # to check against global limit per save file of 16'000 objects
            lastUpdated = self.readable_timestamp(k["LastUpdateTimestamp"])
            self.parse_galactic_address(k["GalacticAddress"])
            btype = k["BaseType"]["PersistentBaseTypes"]
            # base position cartesian --> spherical
            x = k["Position"][0]
            y = k["Position"][1]
            z = k["Position"][2]
            x2py2 = x*x+y*y
            posR =  f"{np.sqrt(x2py2 + z*z):9.1f}"  # planet size + altitude 
            posNS = f"{np.atan2(z, np.sqrt(x2py2))*180/np.pi:7.2f}"  # theta in °
            posEW = f"{np.atan2(y,x)*180/np.pi:7.2f}" # phi in °
            match btype:
                case "ChestMagicInventory":
                    name = 'DeletedBaseCache'
                case "ChestMagicInventory2":
                    name = 'DeletedBaseFreighter'
                case "PlayerShipBase": # Name is always "Default" for corvettes, look up their names
                    name = self.save["BaseContext"]["PlayerStateData"]["ShipOwnership"][k["UserData"]]["Name"]
                case "FreighterBase": # it's name is not necessary, but why not include it
                    name = self.save["BaseContext"]["PlayerStateData"]["PlayerFreighterName"]
                case _: # includes renamed storage crates, which all have their own type (0-9)
                    name = k["Name"] 
            report.writerow([self.ua, self.galaxy, self.glyphs, lastUpdated, f"{parts:5d}",
                             posR, posNS, posEW, f"{btype:18}", name])

            for i in k["Objects"]:
                id = i["ObjectID"]
                lastUpdated = self.readable_timestamp(i["Timestamp"])
                x = f"{i["Position"][0]:10.2f}"
                y = f"{i["Position"][1]:10.2f}"
                z = f"{i["Position"][2]:10.2f}"
                partName = f"{self.mapItemName[id] if id in self.mapItemName else "?":30}"
                detail.writerow([f'{id:20}', partName, x, y, z, lastUpdated, name])

        tsvreport.close()
        tsvdetail.close()
        self.log.info(f"  ... parsed {basecount} bases with {totalparts} parts in total (global limit: 16'000 parts)")
        
    def parse_inventory(self):
        """Extract info about inventories from one save into some tsv files."""
        tsvreport = open(self.fn+".inventories.tsv", 'w', newline='', encoding='utf-8')
        report = csv.writer(tsvreport, delimiter='\t')
        report.writerow(["Stacks", "Techn.", f"{"InventoryType":30}", "InventoryName"])

        tsvdetail = open(self.fn+".inventoryslots.tsv", 'w', newline='', encoding='utf-8')
        detail = csv.writer(tsvdetail, delimiter='\t')
        detail.writerow([f"{"x":2}", f"{"y":2}", f"{"Amount":8}", f"{"id":20}", f"{"seed":10}",  
                         f"{"itemName":30}", f"{"itemCtg":20}", f"{"InventoryType":30}", "InventoryName"])

        self.itemcount = 0
        self.stackcount = 0
        self.techcount = 0
        def parse_slots(slots, inventoryType, InvName):
            """Process one inventory "Slots" object at a time."""
            nonlocal report, detail
            if("Tech" in inventoryType):
                report.writerow([f"{0:6}", f"{len(slots):6}", f"{inventoryType:30}", InvName])
                self.techcount += len(slots)
            else:
                report.writerow([f"{len(slots):6}", f"{0:6}", f"{inventoryType:30}", InvName])
                self.stackcount += len(slots)
            for i in slots:
                amt = i["Amount"]
                self.itemcount += amt if amt > 0 else 0
                try:
                    id = i["Id"].split("#")[0]
                    seed = i["Id"].split("#")[1]
                except:
                    id = i["Id"]
                    seed = ""
                itemName = self.mapItemName[id] if id in self.mapItemName else id
                itemCtg = self.mapItemCtg[id] if id in self.mapItemCtg else "not found"
                x = i["Index"]["X"]
                y = i["Index"]["Y"]
                detail.writerow([f"{x:2}", f"{y:2}", f"{amt:8}", f"{id:20}", f"{seed:10}", 
                                f"{itemName:30}", f"{itemCtg:20}", f"{inventoryType:30}", InvName])

        for inventoryType, o in (self.save["BaseContext"]["PlayerStateData"]).items():
            if("Inventory" in inventoryType): 
                if "Slots" in o:
                    match inventoryType:
                        case "Inventory_TechOnly":
                            InvName = "Exosuit"
                        case "Inventory":
                            InvName = "Exosuit"
                        case "FreighterInventory":
                            InvName = self.save["BaseContext"]["PlayerStateData"]["PlayerFreighterName"]
                        case "FreighterInventory_TechOnly":
                            InvName = self.save["BaseContext"]["PlayerStateData"]["PlayerFreighterName"]
                        case _:
                            InvName = o["Name"]
                    if InvName == "":
                        InvName = "None"
                    parse_slots(o["Slots"], inventoryType, InvName)

        for s in (self.save["BaseContext"]["PlayerStateData"]["ShipOwnership"]):
            parse_slots(s["Inventory"]["Slots"], "ShipInventory", s["Name"])
            parse_slots(s["Inventory_TechOnly"]["Slots"], "ShipTech", s["Name"])

        for s in (self.save["BaseContext"]["PlayerStateData"]["VehicleOwnership"]):
            parse_slots(s["Inventory"]["Slots"], "ExocraftInventory", s["Name"])
            parse_slots(s["Inventory_TechOnly"]["Slots"], "ExocraftTech", s["Name"])

        for s in (self.save["BaseContext"]["PlayerStateData"]["Multitools"]):
            parse_slots(s["Store"]["Slots"], "MultitoolTech", s["Name"])

        tsvreport.close()
        tsvdetail.close()
        self.log.info(f"  ... parsed {self.itemcount} items in {self.stackcount} inventory slots including {self.techcount} installed tech")

    def parse_discoveries(self):
        """Extract info about discoveries from one save into some tsv files."""
        tsvreport = open(self.fn+".discoveries.tsv", 'w', newline='', encoding='utf-8')
        report = csv.writer(tsvreport, delimiter='\t')
        report.writerow([" stored", "renamed", "   mine", "mynamed", "pending", f"{"dtype":20}"])

        tsvdetail = open(self.fn+".discoverydata.tsv", 'w', newline='', encoding='utf-8')
        detail = csv.writer(tsvdetail, delimiter='\t')
        detail.writerow([f"{"ua":14}", "RId", f"{"glyphs":12}", f"{"timeStamp":22}", f"{"dtype":20}", "newName", "by"])
        
        totalcount = 0
        subcount = dict()
        namedcount = dict()
        mycount = dict()
        mynamedcount = dict()
        pendingcount = dict()
        myID = self.save["CommonStateData"]["UsedDiscoveryOwnersV2"][0]["UID"]
        
        for r in (self.save["DiscoveryManagerData"]["DiscoveryData-v1"]["Store"]["Record"]):
            dtype = r["DD"]["DT"]
            byID = r["OWS"]["UID"]
            by = r["OWS"]["USN"]
            try: 
                newName= r["DM"]["CN"]
            except:
                newName = "none"
            timeStamp = self.readable_timestamp(r["OWS"]["TS"])
            self.parse_galactic_address(r["DD"]["UA"])
            detail.writerow([self.ua, self.galaxy, self.glyphs, timeStamp, f"{dtype:20}", newName, by])
            totalcount += 1
            try:
                subcount[dtype] += 1
            except:
                subcount[dtype] = 1
            if newName != "none" and newName != "":
                try:
                    namedcount[dtype] += 1
                except:
                    namedcount[dtype] = 1
            if byID == myID:
                try:
                    mycount[dtype] += 1
                except:
                    mycount[dtype] = 1
            if byID == myID and newName != "none" and newName != "":
                try:
                    mynamedcount[dtype] += 1
                except:
                    mynamedcount[dtype] = 1

        for r in (self.save["DiscoveryManagerData"]["DiscoveryData-v1"]["Available"]):
            dtype = r["DD"]["DT"]
            timeStamp = self.readable_timestamp(r["TSrec"])
            self.parse_galactic_address(r["DD"]["UA"])
            detail.writerow([self.ua, self.galaxy, self.glyphs, timeStamp, f"{dtype:20}", "none", "minePendingUpload"]) 
            try:
                pendingcount[dtype] += 1
            except:
                pendingcount[dtype] = 1

        for dtype in subcount:
            report.writerow([
                f"{subcount[dtype]:7}", 
                f"{namedcount[dtype] if dtype in namedcount else 0:7}", 
                f"{mycount[dtype] if dtype in mycount else 0:7}", 
                f"{mynamedcount[dtype] if dtype in mynamedcount else 0:7}", 
                f"{pendingcount[dtype] if dtype in pendingcount else 0:7}",
                f"{dtype:20}", 
            ])

        tsvreport.close()
        tsvdetail.close()
        self.log.info(f"  ... parsed {totalcount} discoveries")


    def parse_varia(self):
        """Extract various attribute values in unpivoted form."""
        tsvdetail = open(self.fn+".varia.tsv", 'w', newline='', encoding='utf-8')
        detail = csv.writer(tsvdetail, delimiter='\t')
        detail.writerow([f"{"SubjectType":20}", f"{"SubjectName":30}", f"{"Attribute":20}", "Value"])

        subjects = 0
        def parse_ship_or_tool(obj, type):
            n = f"{"Unnamed" if obj["Name"] == "" else obj["Name"]:30}" 
            t = f"{type:20}"
            r = obj["Resource"]["Filename"].replace(".SCENE.MBIN", "").replace("MODELS/COMMON/", "")
            if r != "": detail.writerow([t, n, f"{"Resource":20}", r])
            try:
                detail.writerow([t, n, f"{"class":20}",  obj["Inventory"]["Class"]["InventoryClass"]])
            except:
                pass
            try:
                detail.writerow([t, n, f"{"class":20}",  obj["Store"]["Class"]["InventoryClass"]])
            except:
                pass
            try:
                for a in obj["Inventory"]["BaseStatValues"]:
                    detail.writerow([t, n, f"{a["BaseStatID"]:20}", a["Value"]])
            except:
                pass
            try:
                for a in obj["Store"]["BaseStatValues"]:
                    detail.writerow([t, n, f"{a["BaseStatID"]:20}", a["Value"]])
            except:
                pass
            return 1

        for s in (self.save["BaseContext"]["PlayerStateData"]["ShipOwnership"]):
            subjects += parse_ship_or_tool(s, "activeShip")
        
        for s in (self.save["BaseContext"]["PlayerStateData"]["ArchivedShipOwnership"]):
            subjects += parse_ship_or_tool(s["Ownership"], "archivedShip")

        for s in (self.save["BaseContext"]["PlayerStateData"]["Multitools"]):
            subjects += parse_ship_or_tool(s, "activeTool")

        for s in (self.save["BaseContext"]["PlayerStateData"]["ArchivedMultitools"]):
            subjects += parse_ship_or_tool(s["MultitoolData"], "archivedTool")
            
        #tsvreport.close() # no point in creating a summary of those (yet)
        tsvdetail.close()
        self.log.info(f"  ... parsed various attributes of {subjects} subjects")

    def readable_timestamp(self, timestampint):
        """Convert integer timestamps from nms to a datetime value (UTC+0?)."""
        return f"{datetime(1970, 1, 1, 0, 0, 0) + timedelta(seconds=timestampint)}:22"

    def parse_galactic_address(self, hexorint):
        """Obtain galactic address data from either a hex or decimal string"""       
        # unify the universal address (ua) as hex code of length 14
        self.ua = f"{int(str(hexorint), 0):014x}".upper() 
        # extract portal glyphs as sequence of 12 hex values:
        self.glyphs = self.ua[0:4]+self.ua[6:14] 
        # extract galaxy index, e.g. 0 for Euklid, 1 for Hilbert etc.
        self.galaxy = self.ua[4:6] 

    def get_readme(self):
        '''Download a recent "README.md" from this script's github.'''
        
        self.log.info("See the file ./download/README.md for further information")
        if "README.md" not in os.listdir("./download/"):
            self.log.info("  ... fetching a recent copy of the README from github")
            u = urlopen("https://raw.githubusercontent.com/bonifarz/NMS-save-parser/refs/heads/main/README.md")
            writeFile("download/README.md", u.read())

    def get_nms_tables(self):
        '''Get "nms extracted tables" from googledocs or from previous csv downloads.'''
        self.mapItemName=dict()
        self.mapItemCtg=dict()
        self.get_one_nms_table('baseparts', '1266802719')
        self.get_one_nms_table('baseobjects', '239438662')
        self.get_one_nms_table('consumables', '1149392929')
        self.get_one_nms_table('products', '984581625')
        self.get_one_nms_table('substances', '66931870')
        self.get_one_nms_table('proctech', '1672062070')
        self.get_one_nms_table('technology', '874018846')
        self.log.info("  ... item dictionaries created")

    def get_one_nms_table(self, sheetname, gid):
        '''Processes one nms extracted table at a time.'''
        try:
            f = open(f"download/{sheetname}.csv", newline='')
            r = csv.reader(f, delimiter=',') 
            self.log.info(f"  ... using saved file ./download/{sheetname}.csv")
        except:
            sheet_id = "1J8WdrubKgo8A9hPY-hbQLq4eVrb3n3lZAgiI2J7ncAU"
            url = (f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}")
            self.log.info(f"  ... fetching {sheetname} from {url}")
            u = urlopen(url)
            resp = u.read()
            writeFile(f"download/{sheetname}.csv",  resp)
            f = open(f"download/{sheetname}.csv", newline='')
            r = csv.reader(f, delimiter=',') 
        for row in r:
            ctg = row.index("Category") if "Category" in row else 0 
            break
        f.seek(0)
        for row in r:
            self.mapItemName["^"+row[1]] = row[0]
            if ctg > 0:
                self.mapItemCtg["^"+row[1]] = sheetname+" - "+row[ctg]

    def get_mapping(self):
        '''Get the "mapping" from monkeyman192's github repo or from a previous json download.'''
        try:
            mappingfilestructure = json.load(open("download/mapping.json"))
            self.log.info("  ... using saved file ./download/mapping.json")
        except:
            u = urlopen("https://github.com/monkeyman192/MBINCompiler/releases/latest/download/mapping.json")
            writeFile("download/mapping.json", u.read())
            mappingfilestructure = json.load(open("download/mapping.json"))
            self.log.info("  ... written ./download/mapping.json as obtained from monkeyman192's github repo")
        self.mapping = dict()
        for i in mappingfilestructure["Mapping"]:
            self.mapping[i["Key"]] = i["Value"]
        self.log.info("  ... save mapping dictionary created")

    def apply_mapping(self, shortsave):
        """Use the "mapping" in a custom hook to get a readable data structure from the obfuscated save data."""
        def hookwithmapping(obj):
            mappedobj = dict()
            try:
                for i in obj:
                    mappedobj[self.mapping[i]] = obj[i]
                return mappedobj
            except:
                return obj
        #convert the bytearray encoding from ansi to utf8, and remove the null byte at its end
        utf8savedata = shortsave.decode("ansi")[:-1].encode("utf-8")
        #then extract the json data structure using our custom hook to apply the name mapping:
        return json.loads(utf8savedata, object_hook=hookwithmapping)