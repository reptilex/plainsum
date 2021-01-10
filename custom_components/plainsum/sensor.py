"""Numeric sum of data coming from a source sensor over time."""
from decimal import Decimal, DecimalException
import logging

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_NAME,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    TIME_DAYS,
    TIME_HOURS,
    TIME_MINUTES,
    TIME_SECONDS,
)
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity

# mypy: allow-untyped-defs, no-check-untyped-defs

_LOGGER = logging.getLogger(__name__)

ATTR_SOURCE_ID = "source"

CONF_SOURCE_SENSOR = "source"
CONF_ROUND_DIGITS = "round"
CONF_UNIT_PREFIX = "unit_prefix"
CONF_UNIT_TIME = "unit_time"
CONF_UNIT_OF_MEASUREMENT = "unit"

# SI Metric prefixes
UNIT_PREFIXES = {None: 1, "k": 10 ** 3, "M": 10 ** 6, "G": 10 ** 9, "T": 10 ** 12}

# SI Time prefixes
UNIT_TIME = {
    TIME_SECONDS: 1,
    TIME_MINUTES: 60,
    TIME_HOURS: 60 * 60,
    TIME_DAYS: 24 * 60 * 60,
}

ICON = "mdi:sigma"

DEFAULT_ROUND = 3

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME): cv.string,
        vol.Required(CONF_SOURCE_SENSOR): cv.entity_id,
        vol.Optional(CONF_ROUND_DIGITS, default=DEFAULT_ROUND): vol.Coerce(int),
        vol.Optional(CONF_UNIT_PREFIX, default=None): vol.In(UNIT_PREFIXES),
        vol.Optional(CONF_UNIT_TIME, default=TIME_HOURS): vol.In(UNIT_TIME),
        vol.Optional(CONF_UNIT_OF_MEASUREMENT): cv.string,
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the sum sensor."""
    plainsum = PlainsumSensor(
        config[CONF_SOURCE_SENSOR],
        config.get(CONF_NAME),
        config[CONF_ROUND_DIGITS],
        config[CONF_UNIT_PREFIX],
        config[CONF_UNIT_TIME],
        config.get(CONF_UNIT_OF_MEASUREMENT),
    )

    async_add_entities([plainsum])


class PlainsumSensor(RestoreEntity):
    """Representation of a sum sensor."""

    def __init__(
        self,
        source_entity,
        name,
        round_digits,
        unit_prefix,
        unit_time,
        unit_of_measurement,
    ):
        """Initialize the sum sensor."""
        self._sensor_source_id = source_entity
        self._round_digits = round_digits
        self._state = 0

        self._name = name if name is not None else f"{source_entity} sum"

        if unit_of_measurement is None:
            self._unit_template = (
                f"{'' if unit_prefix is None else unit_prefix}{{}}{unit_time}"
            )
            # we postpone the definition of unit_of_measurement to later
            self._unit_of_measurement = None
        else:
            self._unit_of_measurement = unit_of_measurement

        self._unit_prefix = UNIT_PREFIXES[unit_prefix]
        self._unit_time = UNIT_TIME[unit_time]

    async def async_added_to_hass(self):
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state:
            try:
                self._state = Decimal(state.state)
            except ValueError as err:
                _LOGGER.warning("Could not restore last state: %s", err)

        @callback
        def calc_sum(event):
            """Handle the sensor state changes."""
            old_state = event.data.get("old_state")
            new_state = event.data.get("new_state")
            if (
                old_state is None
                or old_state.state in [STATE_UNKNOWN, STATE_UNAVAILABLE]
                or new_state.state in [STATE_UNKNOWN, STATE_UNAVAILABLE]
            ):
                return

            if self._unit_of_measurement is None:
                unit = new_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
                self._unit_of_measurement = self._unit_template.format(
                    "" if unit is None else unit
                )

            try:
                # sum of current state of sum_sensor + current defined sensor measure.
                plainsum = Decimal(new_state.state) / self._unit_prefix
                assert isinstance(plainsum, Decimal)
            except ValueError as err:
                _LOGGER.warning("While calculating sum: %s", err)
            except DecimalException as err:
                _LOGGER.warning(
                    "Invalid state (%s > %s): %s", old_state.state, new_state.state, err
                )
            except AssertionError as err:
                _LOGGER.error("Could not calculate sum: %s", err)
            else:
                self._state += plainsum
                self.async_write_ha_state()

        async_track_state_change_event(
            self.hass, [self._sensor_source_id], calc_sum
        )

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return round(self._state, self._round_digits)

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._unit_of_measurement

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {ATTR_SOURCE_ID: self._sensor_source_id}

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return ICON
