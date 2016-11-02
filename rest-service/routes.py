#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding:utf-8
#
# routes.py: Falcon file to serve API routes
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
import falcon
import json
import data_access


class DatasetResource(object):
    def on_get(self, req, resp, dataset_id):
        """Return a HTTP response with all information about one dataset
        """
        dataset = data_access.DatasetDAO()
        resource, err = dataset.get_dataset_by_id(dataset_id)
        if resource is None:
            if err[0] == 404:
                resp.status = falcon.HTTP_404
            else:
                resp.status = falcon.HTTP_500
            textbody = {"status": err[0], "message": err[1]}
            resp.body = json.dumps(textbody)
            return

        response = {
            "dataset": resource,
        }
        resp.body = json.dumps(response)
        resp.content_type = 'application/json'
        resp.status = falcon.HTTP_200


class DatasetFactory(object):
    def on_get(self, req, resp):
        """Return all datasets"""
        dao = data_access.DatasetDAO()

        listdts, err = dao.get_all_datasets()

        if listdts is None:
            if err[0] == 404:
                resp.status = falcon.HTTP_404
            else:
                resp.status = falcon.HTTP_500
            textbody = {"status": err[0], "message": err[1]}
            resp.body = json.dumps(textbody)
            return

        response = [{"dataset": dtst} for dtst in listdts]
        resp.body = json.dumps(response)
        resp.content_type = 'application/json'
        resp.status = falcon.HTTP_200

    def on_post(self, req, resp):
        """Makes HTTP response to receive POST /datasets requests

        This method will create a new empty dataset, and returns a 201 CREATED
        with Location header filled with the URI of the dataset.
        """
        dao = data_access.DatasetDAO()

        # Get dataset type
        try:
            dts_type = int(req.get_param("type"))
        except Exception:
            # Fallback to read default type: 0
            dts_type = 0

        dataset_type = dao.get_dataset_types()[dts_type]
        id_dts, err = dao.insert_empty_dataset(dataset_type["class"])

        resp.status = falcon.HTTP_201
        resp.body = "Created"
        resp.location = "/datasets/"+str(id_dts)


class PredictSimilarEntitiesResource(object):
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
        resource, err = dataset_dao.get_dataset_by_id(dataset_id)
        if resource is None:
            if err[0] == 404:
                resp.status = falcon.HTTP_404
            else:
                print(err)
                resp.status = falcon.HTTP_500
            textbody = {"status": err[0], "message": err[1]}
            resp.body = json.dumps(textbody)
            return
        dataset = dataset_dao.build_dataset_object()

        # Get server to do 'queries'
        server, err = dataset_dao.get_server()
        if server is None:
            if err[0] == 409:
                resp.status = falcon.HTTP_409
            else:
                resp.status = falcon.HTTP_500
            textbody = {"status": err[0], "message": err[1]}
            resp.body = json.dumps(textbody)
            return

        # Dig for the limit param on Query Params
        limit = req.get_param('limit')
        if limit is None:
            limit = 10  # Default value
        # Needed because server returns also the identical triple
        limit = int(limit) + 1

        # Dig for the search_k param on Query Params
        try:
            search_k = int(req.get_param('search_k'))
        except Exception:
            search_k = -1

        # If looking for similar_entities given an embedding vector
        if embedding:
            similar_entities = server.similarity_by_embedding(
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

            similar_entities = [{"entity": dataset.get_entity(e_id),
                                 "distance": dist}
                                for e_id, dist in server.similarity_by_id(
                                    entity_id, limit, search_k=search_k)]
            entity_used = {
                "value": dataset.get_entity(entity_id),
                "type": "uri"
            }

        response = {
            "dataset": resource,
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

    def on_post(self, req, resp, dataset_id):
        """Reads the body of request and looks for similar entities

        It is needed a body when asking for similar entities due to an URI
        or a vector can not be parsed very well on the request URI. Reads
        the body of POST request and executes correctly the on_get method.

        The body must contain an entity object, like this:

        { "entity":
          {"value": "http://www.wikidata.org/entity/Q1492", "type": "uri"}
        }

        :param int dataset_id: The dataset identifier on database
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


class TriplesResource():
    """Receives HTTP Request to manage triples on dataset

    This will expect an input on the body similar to This
    {"triples": [{"subject":"Q1492", "predicate":"P17", "object":"Q29"}]}

    """
    def on_post(self, req, resp, dataset_id):
        try:
            extra = "Couldn't decode the input stream (body)."
            body = json.loads(req.stream.read().decode('utf-8'))

            if "triples" not in body:
                extra = "It was expected a JSON object with a 'triples' param"
                print(extra)
                raise KeyError
            if not isinstance(body["triples"], list):
                extra = "The 'triples' param is expected to contain a list"
                print(extra)
                raise ValueError

            for triple in body["triples"]:
                if "subject" not in triple or "predicate" not in triple\
                   or "object" not in triple:
                    extra = ("Error on '{}': All the triples must contain "
                             "'subject', 'predicate' and 'object'").format(
                             triple)
                    raise ValueError

        except (json.decoder.JSONDecodeError, KeyError, ValueError) as err:
            msg = ("Couldn't read body correctly from HTTP request. "
                   "Please, read the documentation carefully and try again. "
                   "Extra info: "+extra)
            resp.body = json.dumps({"status": 400, "message": msg})
            resp.content_type = 'application/json'
            resp.status = falcon.HTTP_400
            return

        dataset_dao = data_access.DatasetDAO()
        resource, err = dataset_dao.get_dataset_by_id(dataset_id)
        if resource is None:
            if err[0] == 404:
                resp.status = falcon.HTTP_404
            else:
                print(err)
                resp.status = falcon.HTTP_500
            textbody = {"status": err[0], "message": err[1]}
            resp.body = json.dumps(textbody)
            return
        # dataset = dataset_dao.build_dataset_object()
        res, err = dataset_dao.insert_triples(body['triples'])
        if res is None:
            if err[0] == 404:
                resp.status = falcon.HTTP_404
            else:
                print(err)
                resp.status = falcon.HTTP_500
            textbody = {"status": err[0], "message": err[1]}
            resp.body = json.dumps(textbody)
            return

        textbody = {"status": 202, "message": "Resources created successfuly"}
        resp.body = json.dumps(textbody)
        resp.content_type = 'application/json'
        resp.status = falcon.HTTP_202

# falcon.API instances are callable WSGI apps
app = falcon.API()

# Resources are represented by long-lived class instances
dataset = DatasetResource()
datasetcreate = DatasetFactory()
similar_entities = PredictSimilarEntitiesResource()
triples = TriplesResource()

# All API routes and the object that will handle each one
app.add_route('/datasets/', datasetcreate)
app.add_route('/datasets/{dataset_id}', dataset)
app.add_route('/datasets/{dataset_id}/triples', triples)
app.add_route('/datasets/{dataset_id}/similar_entities/{entity}',
              similar_entities)
app.add_route('/datasets/{dataset_id}/similar_entities', similar_entities)
