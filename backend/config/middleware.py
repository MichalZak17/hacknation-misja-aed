"""HEAD responses without a body. Django leaves that to the server; runserver strips it, gunicorn sends it, and the
Next.js /api proxy then fails on the extra bytes ("Data after Connection: close"). dane.gov.pl checks every link with
HEAD before downloading it, so this matters for the export endpoints."""


def head_without_body(get_response):
    def middleware(request):
        response = get_response(request)
        if request.method == "HEAD" and not response.streaming:
            length = len(response.content)
            response.content = b""
            response["Content-Length"] = str(length)  # the size a GET would return
        return response

    return middleware
