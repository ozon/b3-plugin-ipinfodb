IPInfoDB Plugin for Big Brother Bot
===================================

This plugin provides a simple interface for [IPInfoDB](http://ipinfodb.com) API.
The Client Object gets a new property that includes a country code.

### Features
- location information obtained from [IPInfoDB](http://ipinfodb.com)
- set country code as client attribute
- Results cached in the DB

### Requirements
- IPInfoDB API key - This API key is free for everyone. You just have to [register](http://ipinfodb.com/register.php).
- latest [B3 Server](http://bigbrotherbot.net)
- [Requests](http://docs.python-requests.org/en/latest/user/install/#install)

Usage
-----

### Installation
1. Copy the file [extplugins/ipinfodb.py](extplugins/ipinfodb.py) into your `b3/extplugins` folder and
[extplugins/conf/plugin_ipinfodb.ini](extplugins/conf/plugin_ipinfodb.ini) into your `b3/conf` folder

2. Import the table structure from [sql/ipinfodb.sql](sql/ipinfodb.sql) to your DB.

3. Add the following line in your b3.xml file (below the other plugin lines)
  ```xml
  <plugin name="ipinfodb" config="@conf/plugin_ipinfodb.ini"/>
  ```

### Configuration
Add your IPInfoDB API key in [extplugins/conf/plugin_ipinfodb.ini](extplugins/conf/plugin_ipinfodb.ini).

### What's next?
Clients now have the ```country``` property which includes the country code.
What do you do with it is up to you.