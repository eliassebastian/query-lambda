import io
import json
from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import ValueTarget
import base64
import tafra

def lambda_handler(event, context):
    """Sample pure Lambda function

    Parameters
    ----------
    event: dict, required
        API Gateway Lambda Proxy Input Format

        Event doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format

    context: object, required
        Lambda Context runtime methods and attributes

        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
    API Gateway Lambda Proxy Output Format: dict

        Return doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
    """

    # try:
    #     ip = requests.get("http://checkip.amazonaws.com/")
    # except requests.RequestException as e:
    #     # Send some context about this error to Lambda Logs
    #     print(e)

    #     raise e

    print("event", event,"context", context, event['isBase64Encoded'], 'test')

    parser = StreamingFormDataParser(headers=event['headers'])
    test = ValueTarget() 
    uploaded_file = ValueTarget()

    parser.register("test", test)
    parser.register("file", uploaded_file)

    if event['isBase64Encoded']:
        body_bytes = base64.b64decode(event['body'])
    else:
        body_bytes = event['body'].encode('utf-8')

    parser.data_received(body_bytes)

    buffer = io.BufferedReader(io.BytesIO(uploaded_file.value))
    wrapper = io.TextIOWrapper(buffer, encoding='utf-8')
    tf = tafra.read_csv(wrapper, guess_rows=10)

    print(tf)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "hello world",
        }),
    }
