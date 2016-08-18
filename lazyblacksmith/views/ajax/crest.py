# -*- encoding: utf-8 -*-
from collections import OrderedDict

from flask import Blueprint
from flask import json
from flask import jsonify
from flask import request
from sqlalchemy.orm.exc import NoResultFound

from . import is_not_ajax
from lazyblacksmith.extension.cache import cache
from lazyblacksmith.models import Activity
from lazyblacksmith.models import ActivityMaterial
from lazyblacksmith.models import IndustryIndex
from lazyblacksmith.models import ItemAdjustedPrice
from lazyblacksmith.models import ItemPrice
from lazyblacksmith.models import SolarSystem
from lazyblacksmith.utils.time import utcnow

import humanize

ajax_crest = Blueprint('ajax_crest', __name__)

@ajax_crest.route('/get_price/<string:item_list>', methods=['GET'])
def get_price(item_list):
    """
    Get prices for all items we need !
    """
    if request.is_xhr:

        item_list = item_list.split(',')

        # get all items price
        item_prices = ItemPrice.query.filter(
            ItemPrice.item_id.in_(item_list)
        )

        item_price_list = {}
        for price in item_prices:
            if price.region_id not in item_price_list:
                item_price_list[price.region_id] = {}

            update_delta = price.updated_at - utcnow()
            item_price_list[price.region_id][price.item_id] = {
                'sell': price.sell_price,
                'buy': price.buy_price,
                'updated_at': humanize.naturaltime(update_delta),
            }

        # get all items adjusted price
        item_adjusted = ItemAdjustedPrice.query.filter(
            ItemAdjustedPrice.item_id.in_(item_list)
        )

        item_adjusted_list = {}
        for item in item_adjusted:
            item_adjusted_list[item.item_id] = item.price

        return jsonify({'prices': item_price_list, 'adjusted': item_adjusted_list})
    else:
        return 'Cannot call this page directly', 403


@ajax_crest.route('/crest/get_index/<int:activity>/<string:solar_system_names>', methods=['GET'])
def get_index_activity(solar_system_names, activity):
    if Activity.check_activity_existence(activity):
        ss_name_list = solar_system_names.split(',')

        # get the solar systems
        solar_systems = SolarSystem.query.filter(
            SolarSystem.name.in_(ss_name_list)
        ).all()

        if solar_systems is None or len(solar_systems) == 0:
            return 'SolarSystems (%s) do not exist' % (solar_system_names), 404

        # put the solar system in a dict
        solar_systems_list = {}
        for system in solar_systems:
            solar_systems_list[system.id] = system.name

        # get the index from the list of solar system
        industry_index = IndustryIndex.query.filter(
            IndustryIndex.solarsystem_id.in_(solar_systems_list.keys()),
            IndustryIndex.activity == activity
        ).all()

        if industry_index is None or len(industry_index) == 0:
            return 'There is no index with SolarSystem(%s) or activity(%s)' % (
                solar_system_names,
                activity
            ), 404

        # and then put that index list into a dict[solar_system_name] = cost_index
        index_list = {}
        for index in industry_index:
            index_list[solar_systems_list[index.solarsystem_id]] = index.cost_index

        return jsonify(index=index_list)
    else:
        return 'This activity does not exist', 500


