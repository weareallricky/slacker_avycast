# Slacker Avycast
Posts avalanche forecast from avalanche.org API to Slack

## Overview
This app should work avalanche centers that use the avalanche.org API. It will post to your desired Slack channel using a Slack API webhook, which you will need to set up in your Slack instance ([Salck API webhook documentation](https://api.slack.com/messaging/webhooks)). The app will periodically check the API and if it finds a new forecast, it will send a forecast overview to Slack.

[Example screenshot](https://imgur.com/a/jPtKQBt)

### Does my avalanche center use the avalanche.org API?
If your avalanche center's website looks like the [Central Oregaon Avalanche Center's](https://www.coavalanche.org/), it is likely relying on the avalanche.org API to retreieve/display avalanche forecast.

You can confirm this by opening the page showing a current forecast (eg [forecast for Central Oregon Cascades](https://www.coavalanche.org/forecasts/#/central-cascades)), and examining the network requests that happen when you load the page using your browser's developer tools. Look for a request to https://api.avalanche.org/ - the "Name" in the console might look something like "product?type=forecast..." ([example screenshot](https://imgur.com/a/sG9a4kb)). When you select that particular request, you should be able to see the full URL, which should look something like 
```https://api.avalanche.org/v2/public/product?type=forecast&center_id=COAA&zone_id=468```

Take note of the values in the URL for "center_id" and "zone_id" - you will need these to configure your instance of Slacker Avycast.


## Installation
This app is written in Python, and expects to be run with Python3.

### Prerequisites
You will need a few Python modules to run this app:
* Requests
* Python-Dateutil
* BeautifulSoup4
* Python-dotenv

Each of these modules can be installed using PIP:
```$ pip install requests python-dateutil beautifulsoup4 python-dotenv```

### Configuration
This app expects a .env file containing configuration settings in order to run. You can copy the .env-example to .env in the same directory, and modify the variables as needed.
```$ cp .env-example .env && vi .env```

Most importantly, you will need to find your avalanche center ID and forecast zone ID - which you can determine from the API call used by your avalanche center to populate its forecast page (see above for details on how to find this, "Does my avalanche center use the avalanche.org API?"). You will also need a Slack API webhook URL.

### Emojis
You can add danger-level images to the avy forecast message in Slack by creating some custom emojis in your Slack instance. Inside the "images" folder, you will find 5 images with filenames that correspond to the 5 levels of the avalanche danger scale (1 - 5). Create a custom emoji for each one using the following naming scheme:
```:avy-danger-1:```
Simply replace the number to correspond with the name of the image file.

## Execution
To execute this app, simply run ```slacker_avycast.py```:\
```$ ./slacker_avycast.py```

This app will run forever until it receives a kill command (eg "ctrl+c") from the user or system. One way to run this on a remote *nix server without having to keep a terminal open forever is to run it inside of a [screen session](https://linuxize.com/post/how-to-use-linux-screen/).
