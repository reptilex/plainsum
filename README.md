# plainsum
Home Assistant integration to sum a sensor (plain sum of values)

This is a blatant adaptation of the integration sensor found here:
[integration sensor](https://www.home-assistant.io/integrations/integration/)

I copied most of the code and changed it to make a plain sum of the source sensor.
The problem I needed to solve is how to get the watts hours my meter was giving me into a utility meter. I experimented with integration sensor, statistics sensor, history sensor. None would give me a plain summed meter sensor. I have an 8266 attached to the s0 interface of my meter which gives me a pulse per watt used, so I just needed to sum all pulses to get the watts used. That sum combined with utility meters no gives me the exact numbers.

This is generic it will just sum up your value until the end of ... the database space :-D , just as an integration sensor would. I just simplified it to not be an integration and not depend on the time.

## Configuration Variables

#### source string Required
The entity ID of the sensor providing numeric readings.

#### name string (Optional, default: source entity ID meter + '_sum')
Name to use in the frontend.

#### round integer (Optional, default: 3)
Round the calculated integration value to at most N decimal places.

#### unit_prefix string (Optional, default: None)
Metric unit to prefix the integration result. Available units are k, M, G and T.