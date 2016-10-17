import falcon
import json
import data_access


class DatasetResource(object):
    def on_get(self, req, resp, dataset_id):
        dataset = data_access.DatasetDAO()
        resource = dataset.get_dataset_by_id(dataset_id)
        resp.body = json.dumps(resource)
        resp.content_type = 'application/json'
        resp.status = falcon.HTTP_200


# falcon.API instances are callable WSGI apps
app = falcon.API()

# Resources are represented by long-lived class instances
dataset = DatasetResource()

# things will handle all requests to the '/things' URL path
app.add_route('/dataset/{dataset_id}', dataset)
