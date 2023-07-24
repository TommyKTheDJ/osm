# osm
Scripts/code for interacting with OSM - Online Scout Manager

## Risk Assessments

[add_risk_assessment.py](./add_risk_assessment.py) requires an Excel sheet called risk_assessment.xlsx in the same path with the following column headers (with example risk).

|Hazard|Who|Controls|Check|
|---|---|---|---|
|Trips and falls: Person trips or falls over obstruction / knocking over gas stove making contact with a fire or hot gas stove giving rise to injury.|All activity participants.|Fires / BBQ located away from natural obstructions e.g.; trees roots / stumps, fences, rocks & boulders etc.<br>Safe obstruction free area maintained around fire / BBQ <br>Fires / BBQs ‘laid’ in defined areas away from activities and fenced where appropriate <br>Supervision over patrol/campsite and fire layout (e.g.; back of HQ) <br>Camp site inspections and safety briefings <br>Campfire activities subject to adult leader supervision <br>Gas bottle to be in upright position on flat surface, within a well ventilated space, gas bottle should not be placed in dip. <br>Gas stoves to be set up on firm surface to be checked by a leader for stability prior to use. <br>Gas to be connected prior to use and disconnected after each use by a leader. Initial ignition by a leader. Length of connection hoses kept to a minimum with spare hose lengths coiled and secured.|July 2023: checked|

To run this you need to create an OAuth application in OSM (Settings > My Account Details > Developer Tools > OAuth) and then paste the values for the `client_id` and `client_secret` into the script.

Also, you will need to add your own `section_id` value.

You can get this by using developer tools in your browser and viewing the request headers when you're clicking around.
Alternatively you can try this API call: https://documenter.getpostman.com/view/66995/online-scout-manager/RW1emdfP#99c5fe13-8877-7308-c2fb-897f0436b908

A script for trying this is here: [get-sections.py](./get-sections.py)
