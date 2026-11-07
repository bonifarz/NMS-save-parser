# NMS save parser

This lightweight python script parses save data from NO MANS SKY (NMS) and extracts some tabular data in tsv format for further analysis.

## File inputs

This script will read any NMS saves (.hg files) that you copy to the `./io/` folder here. This is not meant to edit or recompress any save data. You just copy the files for convenience of batch processing.

If you do not know where your saves are on windows, copy the below text and then press Win+E, Ctrl+L, Ctrl+V, Enter.
```
%appdata%\HelloGames\NMS
```

## File outputs

The script reads and transforms the save data to gather some statistics and details in tabular format. These tab delimited values (.tsv files) are:

* `bases.tsv` - stats about all your bases,
* `baseparts.tsv` - all the base parts they are composed of,
* `inventories.tsv` - stats about all your inventories,
* `inventoryslots.tsv` - all the items and installed tech they contain,
* `discoveries.tsv` - stats from your discovery manager,
* `discoverydata.tsv` - who discovered what, where and when in there.

They can be imported to your favourite spreadsheet or BI software. Or simply put: Just copy-paste the text to work with the tables.

The script also generates json files that contain the full content of the save data. These are not necessary and their creation steps can be commented out.

* `long.json` - full content of the save in a readable format,
* `obfuscated.json` - for curiosity only, as explained in the next section.

Each of the above files is written (or overwritten) in the  `./io/` folder with the following prefixes, 
* the input file name,
* the save slot name and
* the playtime in seconds,

for example `save3.hg.iHatePermaDeath.71180.inventoryslots.tsv`.

This may be neat in case you want to compare different saves or their history. If you prefer another naming convention, the script should be easy to adapt.

## What this script does

This is where things get technical, but let us break it down here: The small script
* parses any hg files you place in the  `./io/` folder,
* decompresses the save data using [nmssavetool.py by Robert Maupin](https://gist.github.com/Chase-san/16076aaa90429ea6170550926b70f48b),
* *optionally* dumps the result into an `obfuscated.json` file
* applies the key [mapping.json maintained by monkeyman112](https://github.com/monkeyman192/MBINCompiler),
* *optionally* dumps the result into a readable `long.json` file,
* collects some item mappings using the [NMS Extracted Tables by Lo2K and IMonk](https://docs.google.com/spreadsheets/d/1J8WdrubKgo8A9hPY-hbQLq4eVrb3n3lZAgiI2J7ncAU/),
* downloads the data for these mappings to the folder `./download/`,
* skips the download of any file that is already sitting there,
* and gathers some statistics and details as described above.

## File downloads

The mappings mentioned above are not provided with the code here, but rather pulled from the above sources. The following files are kept in the `./download/` folder, so the content is only fetched  for a fresh install or to get an update (of any deleted file). Apart from the `mapping.json`, these are the following tabs of the *NMS Extracted Tables*,
* `baseparts.csv`,
* `baseobjects.csv`,
* `consumables.csv`
* `products .csv`,
* `substances.csv`,
* `proctech.csv`,
* `technology.csv`,

which contain plenty of additional information, that may be useful for further custom scripting. Good stuff.

## Requirements

The repo here does **currently not** contain any pre-compiled binaries (e.g. .exe files).

The functions of the parser use standard libraries only. However, they rely on the included `nmssavetool.py`'s decompress function, which depends on the `lz4` package. A `requirements.txt` with just one line for this single dependency may look like a joke. But if you add more for your own experiments, it may help to refresh it e.g. with a `pip freeze > requirements.txt` on your venv.

## If you are new to python

Then the requirements section was probably some incomprehensible gibberish - Sorry for that. There are various IDEs for python, and VS Code may be a good choice to get started. More info on that one here:

https://code.visualstudio.com/docs/python/python-tutorial

In a nut shell:
* have pyhton and some IDE installed
* get a clone (or download a zip) of the repository
* open the (unzipped) folder in your IDE (e.g. in VS Code)
* create a venv (e.g. Ctrl+Shift+P, create environment)
* install packages there (e.g. `pip install` in a terminal)
* run `main.py` (e.g. button or `py .` in a terminal)

## Inspirations and honourable mentions

I started this small experiment after exploring some sources and database bits of modding tools like the awesome [NMSSaveEditor by goatfungus](https://github.com/goatfungus/NMSSaveEditor). I wondered if the feature to export a json could be replicated in a simple manner and found a charmingly whacky workaround in the form of [lenny009's NMS-Save-Decoder](https://github.com/NMSCD/NMS-Save-Decoder). Cool, I thought, wrapping this up in python could be a nice exercise, so that it gets super convenient to analyse the save, for example like [nms-weasel's base part count](https://github.com/weasel-nms/NMS-base-part-count/tree/main) does. Well, here we are. I hope it will be useful for some of you NMS nerds out there.

Cheers and happy exploring, DrBonifarz

## References

1. [nmssavetool.py by Robert Maupin](https://gist.github.com/Chase-san/16076aaa90429ea6170550926b70f48b)
2. [mapping.json maintained by monkeyman112](https://github.com/monkeyman192/MBINCompiler)
3. [NMS Extracted Tables by Lo2K and IMonk](https://docs.google.com/spreadsheets/d/1J8WdrubKgo8A9hPY-hbQLq4eVrb3n3lZAgiI2J7ncAU/)
4. [NMSSaveEditor by goatfungus](https://github.com/goatfungus/NMSSaveEditor)
5. [lenny009's NMS-Save-Decoder](https://github.com/NMSCD/NMS-Save-Decoder)
6. [nms-weasel's base part count](https://github.com/weasel-nms/NMS-base-part-count/tree/main)