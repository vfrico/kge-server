import falcon
import json
import data_access


class DatasetResource(object):
    def on_get(self, req, resp, dataset_id):
        dataset = data_access.DatasetDAO()
        resource, dataset = dataset.get_dataset_by_id(dataset_id)
        if resource is None:
            if dataset[0] == 404:
                resp.status = falcon.HTTP_404
            else:
                resp.status = falcon.HTTP_500
            resp.body = json.dumps({"status": dataset[0],
                                    "message": dataset[1]})
            return

        response = {
            "dataset": resource,
        }
        resp.body = json.dumps(response)
        resp.content_type = 'application/json'
        resp.status = falcon.HTTP_200


class PredictSimilarEntitiesResource(object):
    def on_get(self, req, resp, dataset_id, entity):
        # Params: ?limit=(int: limit)
        dataset_dao = data_access.DatasetDAO()
        resource, dataset = dataset_dao.get_dataset_by_id(dataset_id)
        if resource is None:
            if dataset[0] == 404:
                resp.status = falcon.HTTP_404
            else:
                resp.status = falcon.HTTP_500
            resp.body = json.dumps({"status": dataset[0],
                                    "message": dataset[1]})
            return

        server, err = dataset_dao.get_server()
        if server is None:
            if err[0] == 409:
                resp.status = falcon.HTTP_409
            else:
                resp.status = falcon.HTTP_500
            resp.body = json.dumps({"status": err[0],
                                    "message": err[1]})
            return
        entity_id = dataset.get_entity_id(entity)

        # Obtain the limit param from Query Params
        limit = req.get_param('limit')
        if limit is None:
            limit = 10  # Default value

        similar_entities = [dataset.get_entity(id) for id in
                            server.similarity_by_id(entity_id, limit)]
        response = {
            "dataset": resource,
            "similar_entities": {
                "entity": entity,
                "limit": len(similar_entities),
                "response": similar_entities
            }
        }
        resp.body = json.dumps(response)
        resp.content_type = 'application/json'
        resp.status = falcon.HTTP_200


# falcon.API instances are callable WSGI apps
app = falcon.API()

# Resources are represented by long-lived class instances
dataset = DatasetResource()
similar_entities = PredictSimilarEntitiesResource()

# All API routes and the object that will handle each one
app.add_route('/dataset/{dataset_id}', dataset)
app.add_route('/dataset/{dataset_id}/similar_entities/{entity}',
              similar_entities)
