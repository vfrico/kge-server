#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding:utf-8
#
# dataset_prediction.py: Falcon file to manage prediction resources
# Copyright (C) 2016  Víctor Fernández Rico <vfrico@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json
import copy
import falcon
import kgeserver.server as server
import endpoints.common_hooks as common_hooks

# Import parent directory (data_access)
import sys
sys.path.insert(0, '..')
try:
    import data_access
    import async_server.tasks as async_tasks
except ImportError:
    raise


def read_pair_list(req, resp, resource, params):
    try:
        body = common_hooks.read_body_as_json(req)

        if "distance" not in body:
            raise falcon.HTTPMissingParam("distance")

        if not isinstance(body["distance"], list) and\
           len(body["distance"]) != 2:
            msg = ("The param 'distance' must contain a list of two"
                   "entities.")
            raise falcon.HTTPInvalidParam(msg, "distance")

        params["entities_pair"] = (body["distance"][0], body["distance"][1])

    except KeyError as err:
        raise falcon.HTTPMissingParam(err(str))


class PredictSimilarEntitiesResource(object):
    # TODO: Refactor this class using hooks
    def on_get(self, req, resp, dataset_id, entity, embedding=False):
        """Makes HTTP response for a SimilarEntities search

        It may be used directly with get, but it is discouraged. This method
        does not return nothing, but makes a http request with Falcon.

        :param int dataset_id: The dataset identifier on database
        :param string entity: Can be either identifier or embedding vector
        :param boolean embedding: True if entity param is an embedding
        :query int limit: Limit of similar entities returned.
                          By default is set to 10
        :query int search_k: Maximum number of nodes where the search is made.
                             The higher this param is, the higher quality is,
                             but the performance is worse. Defaults to -1
        :returns: None
        """
        # Get dataset
        dataset_dao = data_access.DatasetDAO()
        dataset_dto, err = dataset_dao.get_dataset_by_id(dataset_id)
        if dataset_dto is None:
            raise falcon.HTTPNotFound(description=str(err))

        # Ignore dataset status. May produce unpredictable results
        ignore = req.get_param_as_bool("ignore_status")
        if ignore is None:
            ignore = False

        dataset = dataset_dao.build_dataset_object(dataset_dto)  # TODO: design

        # Get server to do 'queries'
        search_index, err = dataset_dao.get_search_index(dataset_dto,
                                                         ignore_status=ignore)
        if search_index is None:
            msg_title = "Dataset not ready perform search operation"
            raise falcon.HTTPConflict(title=msg_title, description=str(err))
        # TODO: Maybe extract server management anywhere to simplify this
        search_server = server.Server(search_index)

        # Dig for the limit param on Query Params
        limit = req.get_param_as_int('limit')
        if limit is None:
            limit = 10  # Default value
        # Needed because server returns also the identical triple
        limit = int(limit) + 1

        # Dig for the search_k param on Query Params
        search_k = req.get_param_as_int('search_k')
        if search_k is None:
            search_k = -1

        # If looking for similar_entities given an embedding vector
        if embedding:
            similar_entities = search_server.similarity_by_embedding(
                entity, limit, search_k=search_k)
            similar_entities = [{"entity": dataset.get_entity(e_id),
                                 "distance": dist}
                                for e_id, dist in similar_entities]

            entity_used = {
                "value": entity,  # Will be an embedding vector
                "type": "embedding"
            }
        # If looking for similar_entities given an entity
        else:
            entity_id = dataset.get_entity_id(entity)
            if entity_id is None:
                raise falcon.HTTPNotFound(
                    description="The {} entity can't be found inside dataset."
                    .format(entity))
            sim_entities = search_server.similarity_by_id(
                entity_id, limit, search_k=search_k)
            similar_entities = [{"entity": dataset.get_entity(e_id),
                                 "distance": dist}
                                for e_id, dist in sim_entities]
            entity_used = {
                "value": dataset.get_entity(entity_id),
                "type": "uri"
            }

        response = {
            "dataset": dataset_dto.to_dict(),
            "similar_entities": {
                "entity": entity_used,
                "limit": len(similar_entities),
                "search_k": search_k,
                "response": similar_entities
            }
        }
        resp.body = json.dumps(response)
        resp.content_type = 'application/json'
        resp.status = falcon.HTTP_200

    @falcon.before(common_hooks.check_dataset_exsistence)
    def on_post(self, req, resp, dataset_id, dataset_dto):
        """Reads the body of request and looks for similar entities

        It is needed a body when asking for similar entities due to an URI
        or a vector can not be parsed very well on the request URI. Reads
        the body of POST request and executes correctly the on_get method.

        The body must contain an entity object, like this:

        { "entity":
          {"value": "http://www.wikidata.org/entity/Q1492", "type": "uri"}
        }

        :param int dataset_id: The dataset identifier on database
        :param DTO dataset_dto: The Dataset DTO from dataset_id (from hook)
        """
        body = json.loads(req.stream.read().decode('utf-8'))
        if 'entity' in body and 'type' in body['entity']:
            if body['entity']['type'].lower() == "uri":
                self.on_get(req, resp, dataset_id, body['entity']['value'])
                return
            if body['entity']['type'].lower() == "embedding":
                self.on_get(req, resp, dataset_id,
                            body['entity']['value'], embedding=True)
                return
            else:
                errmsg = ("The type '{}' of the entity {} is not recognized. "
                          "Please, take a look to the documentation.").format(
                    body['entity']['type'], body['entity'])
        else:
            errmsg = ("Must contain a entity object in json. "
                      "Please, take a look to the documentation.")
            print(errmsg)
        resp.body = json.dumps({"status": 400, "message": errmsg})
        resp.content_type = 'application/json'
        resp.status = falcon.HTTP_400


class DistanceTriples():
    @falcon.before(read_pair_list)
    @falcon.before(common_hooks.check_dataset_exsistence)
    def on_post(self, req, resp, dataset_id, dataset_dto, entities_pair):
        """This method return the true distance between two entities

        {"distance":
            ["http://www.wikidata.org/entity/Q1492",
             "http://www.wikidata.org/entity/Q2807"]
        }

        :param int dataset_id: The dataset identifier on database
        :param DTO dataset_dto: The Dataset DTO from dataset_id (from hook)
        :param tuple entities_pair: A pair of entities (from hook)
        :returns: A distance attribute, float number
        :rtype: dict
        """
        dataset_dao = data_access.DatasetDAO()
        dataset = dataset_dao.build_dataset_object(dataset_dto)  # TODO: design

        # Get server to do 'queries'
        search_index, err = dataset_dao.get_search_index(dataset_dto)
        if search_index is None:
            msg_title = "Dataset not ready perform search operation"
            raise falcon.HTTPConflict(title=msg_title, description=str(err))
        # TODO: Maybe extract server management anywhere to simplify this
        search_server = server.Server(search_index)
        entity_x, entity_y = entities_pair
        id_x = dataset.get_entity_id(entity_x)
        id_y = dataset.get_entity_id(entity_y)
        if id_x is None or id_y is None:
            raise falcon.HTTPNotFound(
                description=("The {} id from entity {} or the {} id from {} "
                             "entity can't be found on the dataset")
                .format(id_x, entity_x, id_y, entity_y))

        dist = search_server.distance_between_entities(id_x, id_y)

        resp.body = json.dumps({"distance": dist})
        resp.content_type = 'application/json'
        resp.status = falcon.HTTP_200


class SuggestEntityName():
    @falcon.before(common_hooks.check_dataset_exsistence)
    def on_post(self, req, resp, dataset_id, dataset_dto):
        """Return suggests to use with autocomplete

        This method will return suggestions to be used on frontend while users
        input the entity name.

        TODO: this should only return entities that exists on dataset, right
        now returns all possible entities.

        :param int dataset_id: The id of the dataset to autocomplete
        :param DTO dataset_dto: The Dataset DTO from dataset_id (from hook)
        :param str input: The input to autocomplete (from body)
        :returns: A list with entities and full text
        :rtype: Object
        """
        try:
            body = common_hooks.read_body_as_json(req)
            input_text = body['input']
        except KeyError as err:
            raise falcon.HTTPMissingParam("input")
        entity_dao = data_access.EntityDAO(dataset_dto.dataset_type,
                                           dataset_id)

        # Extract suggestion from elasticsearch
        suggestion = entity_dao.suggest_entity(input_text)

        # Return a response
        resp.body = json.dumps(suggestion)
        resp.content_type = 'application/json'
        resp.status = falcon.HTTP_200
