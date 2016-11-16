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
import kgeserver.server as server
import async_server.tasks as async_tasks
import async_server.celery as celery_server


class DatasetResource(object):
    def on_get(self, req, resp, dataset_id):
        """Return a HTTP response with all information about one dataset
        """
        dataset = data_access.DatasetDAO()
        resource, err = dataset.get_dataset_by_id(dataset_id)
        if resource is None:
            raise falcon.HTTPNotFound(description=str(err))

        response = {
            "dataset": resource.to_dict(),
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
            raise falcon.HTTPNotFound(description=str(err))

        response = [{"dataset": dtst.to_dict()} for dtst in listdts]
        resp.body = json.dumps(response)
        resp.content_type = 'application/json'
        resp.status = falcon.HTTP_200

    def on_post(self, req, resp):
        """Makes HTTP response to receive POST /datasets requests

        This method will create a new empty dataset, and returns a 201 CREATED
        with Location header filled with the URI of the dataset.
        """
        # graph_pattern = None
        # try:
        #     body = json.loads(req.stream.read().decode('utf-8'))
        #     if "graph_pattern" in body:
        #         graph_pattern = body["graph_pattern"]
        # except json.decoder.JSONDecodeError as err:
        #     print(err)

        dao = data_access.DatasetDAO()
        # Get dataset type
        try:
            dts_type = int(req.get_param("dataset_type"))
        except Exception:
            # Fallback to read default type: 0
            dts_type = 0

        dataset_type = dao.get_dataset_types()[dts_type]["class"]
        id_dts, err = dao.insert_empty_dataset(dataset_type)

        # Dataset created, evrything is done
        resp.status = falcon.HTTP_201
        resp.body = "Created"
        resp.location = "/datasets/"+str(id_dts)
        # else:
        #     dtset = dao.build_dataset_path()
        #
        #     # Generate the dataset with initial graph pattern
        #     task = async_tasks.insert_triples_from_graph_pattern.delay(
        #             dtset, graph_pattern)
        #
        #     # Create a new task
        #     task_dao = data_access.TaskDAO()
        #     task_obj, err = task_dao.add_task_by_uuid(task.id)
        #     if task_obj is None:
        #         raise falcon.HTTPNotFound(description=str(err))
        #     task_obj["next"] = "/datasets/"+str(id_dts)
        #     task_dao.update_task(task_obj)
        #
        #     msg = "Task {} created successfuly".format(task_obj['id'])
        #     textbody = {"status": 202, "message": msg}
        #     resp.location = "/tasks/"+str(task_obj['id'])
        #     resp.body = json.dumps(textbody)
        #     resp.content_type = 'application/json'
        #     resp.status = falcon.HTTP_202


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
        dataset_dto, err = dataset_dao.get_dataset_by_id(dataset_id)
        if dataset_dto is None:
            raise falcon.HTTPNotFound(description=str(err))

        dataset = dataset_dao.build_dataset_object(dataset_dto)  # TODO: design

        # Get server to do 'queries'
        search_index, err = dataset_dao.get_search_index(dataset_dto)
        if search_index is None:
            msg_title = "Dataset not ready perform search operation"
            raise falcon.HTTPConflict(title=msg_title, description=str(err))
        # TODO: Maybe extract server management anywhere to simplify this
        search_server = server.Server(search_index)

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

            similar_entities = [{"entity": dataset.get_entity(e_id),
                                 "distance": dist}
                                for e_id, dist in search_server.similarity_by_id(
                                    entity_id, limit, search_k=search_k)]
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


class DistanceTriples():
    def on_post(self, req, resp, dataset_id):
        """This method return the true distance between two entities

        {"distance":
            ["http://www.wikidata.org/entity/Q1492",
             "http://www.wikidata.org/entity/Q2807"]
        }
        """
        try:
            extra = "Couldn't decode the input stream (body)."
            body = json.loads(req.stream.read().decode('utf-8'))

            if "distance" not in body:
                raise falcon.HTTPMissingParam("distance")

            if not isinstance(body["distance"], list) and\
               len(body["distance"]) != 2:
                msg = ("The param 'distance' must contain a list of two"
                       "entities.")
                raise falcon.HTTPInvalidParam(msg, "distance")

            # Redefine variables
            entity_x = body["distance"][0]
            entity_y = body["distance"][1]

        except (json.decoder.JSONDecodeError, KeyError,
                ValueError, TypeError) as err:
            print(err)
            err_title = "HTTP Body request not loaded correctly"
            msg = ("The body couldn't be correctly loaded from HTTP request. "
                   "Please, read the documentation carefully and try again. "
                   "Extra info: "+extra)
            raise falcon.HTTPBadRequest(title=err_title, description=msg)

        # Get dataset
        dataset_dao = data_access.DatasetDAO()
        dataset_dto, err = dataset_dao.get_dataset_by_id(dataset_id)
        if dataset_dto is None:
            raise falcon.HTTPNotFound(description=str(err))

        dataset = dataset_dao.build_dataset_object(dataset_dto)  # TODO: design

        # Get server to do 'queries'
        search_index, err = dataset_dao.get_search_index(dataset_dto)
        if search_index is None:
            msg_title = "Dataset not ready perform search operation"
            raise falcon.HTTPConflict(title=msg_title, description=str(err))
        # TODO: Maybe extract server management anywhere to simplify this
        search_server = server.Server(search_index)

        id_x = dataset.get_entity_id(entity_x)
        id_y = dataset.get_entity_id(entity_y)

        dist = search_server.distance_between_entities(id_x, id_y)

        resp.body = json.dumps({"distance": dist})
        resp.content_type = 'application/json'
        resp.status = falcon.HTTP_200


class GenerateTriplesResource():
    def on_post(self, req, resp, dataset_id):
        """Generates a task to insert triples on dataset. Async petition.

        Reads from body the parameters such as SPARQL queries

        {"generate_triples":
            {
                "graph_pattern": "<SPARQL Query>",
                "levels": 2
            }
        }

        :param id dataset_id: The dataset to insert triples into
        """
        try:
            extra = "Couldn't decode the input stream (body)."
            body = json.loads(req.stream.read().decode('utf-8'))

            if "generate_triples" not in body:
                extra = ("It was expected a JSON object with a "
                         "'generate_triples' param")
                raise KeyError
            json_rpc = body['generate_triples']
            if "levels" not in json_rpc:
                extra = ("The 'generate_triples' JSON object must contain"
                         "level attribute")
                raise KeyError
        except (json.decoder.JSONDecodeError, KeyError,
                ValueError, TypeError) as err:
            msg = ("Couldn't read body correctly from HTTP request. "
                   "Please, read the documentation carefully and try again. "
                   "Extra info: "+extra)
            resp.body = json.dumps({"status": 400, "message": msg})
            resp.content_type = 'application/json'
            resp.status = falcon.HTTP_400
            return

        dataset_dao = data_access.DatasetDAO()
        dataset_dto, err = dataset_dao.get_dataset_by_id(dataset_id)
        if dataset_dto is None:
            raise falcon.HTTPNotFound(description=str(err))

        # Generate the filepath to the dataset
        dtset_path = dataset_dto.get_binary_dataset()

        # Read arguments from body
        graph_pattern = json_rpc.pop("graph_pattern")
        levels = json_rpc.pop("levels")

        # Launch async task
        task = async_tasks.generate_dataset_from_sparql.delay(
                dtset_path, graph_pattern, levels)

        # Create a new task
        task_dao = data_access.TaskDAO()
        task_obj, err = task_dao.add_task_by_uuid(task.id)
        if task_obj is None:
            raise falcon.HTTPNotFound(description=str(err))
        task_obj["next"] = "/datasets/"+dataset_id
        task_dao.update_task(task_obj)

        msg = "Task {} created successfuly".format(task_obj['id'])
        textbody = {"status": 202, "message": msg}
        resp.location = "/tasks/"+str(task_obj['id'])
        resp.body = json.dumps(textbody)
        resp.content_type = 'application/json'
        resp.status = falcon.HTTP_202


class DatasetIndex():
    # TODO: Save anywhere the number of trees used
    def on_post(self, req, resp, dataset_id):
        """Generates a search index to perform data lookups operations.

        This task may take long time to complete, so it uses tasks.

        :query int n_trees: The number of trees generated
        """
        dataset_dao = data_access.DatasetDAO()
        dataset_dto, err = dataset_dao.get_dataset_by_id(dataset_id)
        if dataset_dto is None:
            raise falcon.HTTPNotFound(description=str(err))

        # Check actual status of the dataset
        if not dataset_dto.is_trained():
            dataset_status = dataset_dto.status
            err_title = "The dataset is not in correct state"
            msg = "The dataset has {} status and is not ready to be indexed"
            raise falcon.HTTPConflict(title=err_title,
                                      description=msg.format(dataset_status))

        # Dig for the param on Query Params
        try:
            n_trees = int(req.get_param('n_trees'))
        except ValueError:
            n_trees = None

        # Call to the task
        task = async_tasks.build_search_index.delay(dataset_id, n_trees)

        # Create the new task
        task_dao = data_access.TaskDAO()
        task_obj, err = task_dao.add_task_by_uuid(task.id)
        if task_obj is None:
            raise falcon.HTTPNotFound(description=str(err))

        msg = "Task {} created successfuly".format(task_obj['id'])
        textbody = {"status": 202, "message": msg}
        resp.location = "/tasks/"+str(task_obj['id'])
        resp.body = json.dumps(textbody)
        resp.content_type = 'application/json'
        resp.status = falcon.HTTP_202


class DatasetTrain():
    # TODO: Test if works well
    def on_post(self, req, resp, dataset_id):
        """Generates a model that fits the dataset and trains it

        It usually takes several hours for big datasets

        This changes the dataset status from 0 to 1 once finished. To indicate
        dataset cannot be modified, this parameter will be set to a negative
        value.

        :query int algorithm_id: The algorithm used to train the dataset
        """
        dataset_dao = data_access.DatasetDAO()
        dataset_dto, err = dataset_dao.get_dataset_by_id(dataset_id)
        if dataset_dto is None:
            raise falcon.HTTPNotFound(description=str(err))

        # Check if dataset can be trained
        if not dataset_dto.is_untrained():
            dataset_status = dataset_dto.status
            err_title = "The dataset is not in correct state"
            msg = "The dataset has {} status and is not ready to be trained"
            raise falcon.HTTPConflict(title=err_title,
                                      description=msg.format(dataset_status))

        # Dig for the limit param on Query Params
        algorithm_id = req.get_param('algorithm_id')
        if algorithm_id is None:
            raise falcon.HTTPMissingParam("algorithm_id")

        # Obtain the algorithm
        algorithm_dao = data_access.AlgorithmDAO()
        algorithm, err = algorithm_dao.get_algorithm_by_id(algorithm_id)
        if algorithm is None:
            raise falcon.HTTPNotFound(message=str(err))

        # If it all goes ok, add id of algorithm to db
        dataset_dao.set_algorithm(dataset_id, algorithm_id)
        dataset_dao.set_status(dataset_id, -1)

        # Launch async task
        task = async_tasks.train_dataset_from_algorithm.delay(
                                                        dataset_id, algorithm)

        # Create the new task
        task_dao = data_access.TaskDAO()
        task_obj, err = task_dao.add_task_by_uuid(task.id)
        if task_obj is None:
            raise falcon.HTTPNotFound(description=str(err))

        msg = "Task {} created successfuly".format(task_obj['id'])
        textbody = {"status": 202, "message": msg}
        resp.location = "/tasks/"+str(task_obj['id'])
        resp.body = json.dumps(textbody)
        resp.content_type = 'application/json'
        resp.status = falcon.HTTP_202


class TasksResource():
    def on_get(self, req, resp, task_id):
        """Return one task"""
        tdao = data_access.TaskDAO()

        task_obj, err = tdao.get_task_by_id(task_id)
        if task_obj is None:
            raise falcon.HTTPNotFound(description=str(err))

        t_uuid = celery_server.app.AsyncResult(task_obj['celery_uuid'])

        task = {}
        task["state"] = t_uuid.state
        # task["is_ready"] = t_uuid.ready()
        task["id"] = task_obj["id"]

        if t_uuid.state == "SUCCESS":
            # Look if exists some next
            if "next" in task_obj and task_obj["next"] is not None:
                print("This task has next {}".format(task_obj["next"]))
                resp.status = falcon.HTTP_303
                resp.location = task_obj["next"]
            else:
                # print("nothing else")
                pass

        elif t_uuid.state == "STARTED":
            # Get task progress and show to the user
            celery_uuid = "celery-task-progress-"+task_obj['celery_uuid']

            redis = data_access.RedisBackend()
            task_progress = redis.get(celery_uuid)

            try:
                if "progress" in task_progress:
                    task["progress"] = task_progress["progress"]
            except TypeError:
                pass

            resp.status = falcon.HTTP_200

        elif t_uuid.state == "FAILURE":
            task["error"] = {"exception": str(t_uuid.result),
                             "traceback": t_uuid.traceback}

        response = {"task": task}
        resp.body = json.dumps(response)
        resp.content_type = 'application/json'


class TriplesResource():
    """Receives HTTP Request to manage triples on dataset

    This will expect an input on the body similar to This
        {"triples": [
                {
                    "subject": {"value": "Q1492"},
                    "predicate": {"value": "P17"},
                    "object": {"value": "Q29"}
                }
            ] }
    """
    def on_post(self, req, resp, dataset_id):
        try:
            extra = "Couldn't decode the input stream (body)."
            body = json.loads(req.stream.read().decode('utf-8'))

            if "triples" not in body:
                extra = "It was expected a JSON object with a 'triples' param"
                raise KeyError
            if not isinstance(body["triples"], list):
                extra = "The 'triples' param is expected to contain a list"
                raise ValueError

            for triple in body["triples"]:
                if "subject" not in triple or "predicate" not in triple\
                   or "object" not in triple:
                    extra = ("Error on '{}': All the triples must contain "
                             "'subject', 'predicate' and 'object'").format(
                             triple)
                    raise ValueError

        except (json.decoder.JSONDecodeError, KeyError,
                ValueError, TypeError) as err:
            msg = ("Couldn't read body correctly from HTTP request. "
                   "Please, read the documentation carefully and try again. "
                   "Extra info: "+extra)
            resp.body = json.dumps({"status": 400, "message": msg})
            resp.content_type = 'application/json'
            resp.status = falcon.HTTP_400
            return

        dataset_dao = data_access.DatasetDAO()
        dataset_dto, err = dataset_dao.get_dataset_by_id(dataset_id)
        if dataset_dto is None:
            raise falcon.HTTPNotFound(description=str(err))

        # dataset = dataset_dao.build_dataset_object()
        res, err = dataset_dao.insert_triples(dataset_dto, body['triples'])
        if res is None:
            raise falcon.HTTPBadRequest(description=str(err))

        textbody = {"status": 202, "message": "Resources created successfuly"}
        resp.body = json.dumps(textbody)
        resp.content_type = 'application/json'
        resp.status = falcon.HTTP_202


class AlgorithmResource():
    def on_get(self, req, resp, algorithm_id):
        """Shows the representation of the selected algorithm

        :param int algorithm_id: The id of the algorithm
        """
        algorithm_dao = data_access.AlgorithmDAO()

        algorithm, err = algorithm_dao.get_algorithm_by_id(algorithm_id)
        if algorithm is None:
            raise falcon.HTTPNotFound(message=str(err))

        resp.body = json.dumps(algorithm)
        resp.content_type = 'application/json'
        resp.status = falcon.HTTP_200


class AlgorithmFactory():
    def on_get(self, req, resp):
        """Shows the representation of all algorithms available
        """
        algorithm_dao = data_access.AlgorithmDAO()

        algorithms, err = algorithm_dao.get_all_algorithms()
        if algorithms is None:
            raise falcon.HTTPNotFound(message=str(err))

        resp.body = json.dumps(algorithms)
        resp.content_type = 'application/json'
        resp.status = falcon.HTTP_200

    def on_post(self, req, resp):
        """Insert algorithm on the service

        :param dict algorithm: The algorithm to be inserted
        """
        # Read body
        try:
            extra = "Couldn't decode the input stream (body)."
            body = json.loads(req.stream.read().decode('utf-8'))

            if "algorithm" not in body:
                raise falcon.HTTPMissingParam("algorithm")

            # Redefine variables
            user_algorithm = body["algorithm"]

        except (json.decoder.JSONDecodeError, KeyError,
                ValueError, TypeError) as err:
            print(err)
            err_title = "HTTP Body request not loaded correctly"
            msg = ("The body couldn't be correctly loaded from HTTP request. "
                   "Please, read the documentation carefully and try again. "
                   "Extra info: "+extra)
            raise falcon.HTTPBadRequest(title=err_title, description=msg)

        algorithm_dao = data_access.AlgorithmDAO()
        algorithm_id, err = algorithm_dao.insert_algorithm(user_algorithm)
        if algorithm_id is None:
            raise falcon.HTTPBadRequest(title="Missing algorithm param",
                                        description=str(err))

        msg = "Algorithm {} created successfuly".format(algorithm_id)
        textbody = {"status": 202, "message": msg}
        resp.body = json.dumps(textbody)
        resource_path = "/algorithm/{}".format(algorithm_id)
        resp.location = resource_path
        resp.status = falcon.HTTP_201


class EmbeddingResource():
    def on_post(self, req, resp, dataset_id):
        """Get the embedding given an entity or a list of entities (URI)

        {"entities": ["Q1492", "Q2807", "Q1"]}

        :query JSON embeddings: List of embeddings
        :returns: A list of list with entities and its embeddings
        :rtype: list
        """
        # Read body
        try:
            extra = "Couldn't decode the input stream (body)."
            body = json.loads(req.stream.read().decode('utf-8'))

            if "entities" not in body:
                raise falcon.HTTPMissingParam("entities")

            if not isinstance(body["entities"], list):
                msg = ("The param 'distance' must contain a list")
                raise falcon.HTTPInvalidParam(msg, "entities")

            # Redefine variables
            entities = body["entities"]

        except (json.decoder.JSONDecodeError, KeyError,
                ValueError, TypeError) as err:
            print(err)
            err_title = "HTTP Body request not loaded correctly"
            msg = ("The body couldn't be correctly loaded from HTTP request. "
                   "Please, read the documentation carefully and try again. "
                   "Extra info: "+extra)
            raise falcon.HTTPBadRequest(title=err_title, description=msg)

        # Extract model
        dataset_dao = data_access.DatasetDAO()

        dataset_dto, err = dataset_dao.get_dataset_by_id(dataset_id)
        if dataset_dto is None:
            raise falcon.HTTPNotFound(
                title="Dataset {} not found".format(dataset_id),
                description="The dataset does not exists. "+str(err))

        istrained = dataset_dto.is_trained()
        if istrained is None or not istrained:
            raise falcon.HTTPConflict(
                title="Dataset has not a valid state",
                description="Dataset {} has a {} state".format(
                    dataset_id, dataset_dto.status))

        # model, err = dataset_dto.get_binary_model()
        # if model is None:
        #     raise falcon.HTTPNotFound(
        #         title="Dataset {} has not any model",
        #         description="The model couldn't be located. "+str(err))

        try:
            result = async_tasks.find_embeddings_on_model(dataset_id, entities)
        except OSError as err:
            filerr = err.filename
            raise falcon.HTTPNotFound(
                title="The file on database couldn't be located",
                description=("A file ({}) has been found on database, but it "
                             "does not exist on filesystem").format(filerr))

        textbody = {"embeddings": result}
        resp.body = json.dumps(textbody)
        resp.status = falcon.HTTP_200


# falcon.API instances are callable WSGI apps
app = falcon.API()

# Resources are represented by long-lived class instances
dataset = DatasetResource()
datasetcreate = DatasetFactory()
similar_entities = PredictSimilarEntitiesResource()
triples = TriplesResource()
gentriples = GenerateTriplesResource()
triples_distance = DistanceTriples()
dataset_train = DatasetTrain()
dataset_index = DatasetIndex()
dataset_embedding = EmbeddingResource()

task_resource = TasksResource()

algorithm_resource = AlgorithmResource()
algorithm_factory = AlgorithmFactory()

# All API routes and the object that will handle each one
app.add_route('/datasets/', datasetcreate)
app.add_route('/datasets/{dataset_id}', dataset)
app.add_route('/datasets/{dataset_id}/triples', triples)
app.add_route('/datasets/{dataset_id}/generate_triples', gentriples)
app.add_route('/datasets/{dataset_id}/distance', triples_distance)
app.add_route('/datasets/{dataset_id}/similar_entities/{entity}',
              similar_entities)
app.add_route('/datasets/{dataset_id}/similar_entities', similar_entities)
app.add_route('/datasets/{dataset_id}/train', dataset_train)
app.add_route('/datasets/{dataset_id}/generate_index', dataset_index)
app.add_route('/datasets/{dataset_id}/embeddings', dataset_embedding)


app.add_route('/tasks/{task_id}', task_resource)

app.add_route('/algorithms/{algorithm_id}', algorithm_resource)
app.add_route('/algorithms/', algorithm_factory)
