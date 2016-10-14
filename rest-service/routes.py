import falcon


class DatasetResource(object):
    def on_get(self, req, resp, dataset_id):
        resp.status = falcon.HTTP_500

# falcon.API instances are callable WSGI apps
app = falcon.API()

# Resources are represented by long-lived class instances
dataset = DatasetResource()

# things will handle all requests to the '/things' URL path
app.add_route('/dataset/{dataset_id}', dataset)
