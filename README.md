# Android Netrunner Discord Draft Bot
Forked from wtodom/anr-draft which works with Slack.

## Install

```python setup.py install```

Or just...

```pip install discord```

since that's the only dependency.

## Setup

Put your bot's token in anrdraft/secrets.json

There is an example file that you can use and rename to secrets.json

## Actions
#### Create Draft

```!create```

The Bot will then give you a draft ID that others will use to join the draft.

#### Join Draft

```!join [draft ID]```

The Bot will tell you when others have joined the draft.

#### Begin Draft

```!start [draft ID]```

Draft will begin and send everyone their first pack of cards.

#### Pick Card

```!pick [card code]```

#### Leave Draft

```!leave [draft ID]```


