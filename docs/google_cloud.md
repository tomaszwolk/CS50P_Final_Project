To create new Google Cloud project with Calendar API follow this steps:

1. Open project picker (ctrl + O) > New project
   
    - Enter Project name
    - Choose Location (if applicable)
    - Create

2. In navigation menu (.):
    - APIs & Services
        - Enable APIs & services
        - \+ Enable APIs and services
        - choose Google Calendar API
        - Enable
    - Credentials
        - \+ Create credentials > OAuth client ID
        - Application type: Desktop app > Enter name > Create
        - Download JSON as "credentials.json" to folder where your script is
    - OAuth consent screen
        - Audience > add Test users (emails that you will use in script - Main and Target) 
        - Data Access > Add or remove scopes > Scope: .../auth/calendar.events