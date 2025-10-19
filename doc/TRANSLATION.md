# How to Add your language to this integration

1) Log into github
2) Go to http://github.com/Elwinmage/ha-reefbeat-component
3) Click on Fork (At the upper right between "Watch" and "Star") then "Create a new fork"  <kbd><img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/i18n/fork.png" /></kbd>
4) Click on Create fork

   <kbd><img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/i18n/new_fork.png" /></kbd>
   
## First step, translation for "RSWAVE select form":

5) Go to https://github.com/ElwinmageTest/ha-reefbeat-component/tree/main/custom_components/redsea/const.py
6) Edit the file with the pencil at upper right 

<kbd><img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/i18n/edit_const.png" /></kbd>

7) Go to WAVE_TYPES and WAVES_DIRECTIONS and add a line for each element for your language using your [international code](https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes) (Set 1 column). Don't forget the coma at the end of the old last line:

   Example for french translation:
```
   {"id":"alt",
     "en": "Alternate"
     },
   {"id":"fw",
      "en": "Forward"
   },
```
became:
```
  {"id":"alt",
     "en": "Alternate",
   "fr": "Alternatif"
     },
   {"id":"fw",
      "en": "Forward",
      "fr": "Marche Avant"
      },
```
   8) Once done click on "Commit Change" 
   
   <kbd><img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/i18n/commit_changes.png" /></kbd>
   
   9) Update the commit message and indicate the new language
   10) Select Create a new branche and then "Propose changes" 
   
   <kbd><img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/i18n/propose_changes.png" /></kbd>
   
   11) Then "Create a pull Request" (twice)

   ## Second Step HomeAssistant translation
   
   12) Now go to https://github.com/ElwinmageTest/ha-reefbeat-component/tree/main/custom_components/redsea/translations/en.json
   13) Click on "Copy Raw file" at upper right 
   
   <kbd><img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/i18n/copy_raw.png" /></kbd>
   
   14) Click on "translation" on the tree file at left. 

<img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/i18n/files_tree.png" />
   
   16) Then "Add file" and "Create new file" at upper right.
   
   <kbd><img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/i18n/add_file.png" /></kbd>
   
   17) Paste in edit zone and add the new filename at the top. ***The file name must be the international code ('fr' for French in my example) with the "json" extension***.
   18) Update the right part of the file with your translation, all words after ':' like "ReefBeat configuration", "Add new Device"...
   
   <kbd><img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/i18n/create_i18n_file_2.png" /></kbd>
   
   19) Commit yout changes 
   
   <kbd><img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/i18n/commit_changes.png" /></kbd>
   
   20) Select Create a new branche and then "Propose changes" 
   
   <kbd><img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/i18n/propose_changes.png" /></kbd>
   
   21) Then "Create a pull Request" (twice)
       
       
       
