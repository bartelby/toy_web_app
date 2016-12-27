The project consists of a minimal Flask web app whose requirements are given
in the accompanying PDF file.

To run the web application, do the following:
(1)     Activate the virtual environment. In a command or terminal window
        navigate to the project's top level directory and enter
        the following command: . venv/bin/activate
(2)     Once the virtual environment has been activated, in the same terminal
        window, enter: python admit_one.py
        This starts the web application, which is listening on port 5000.

The web app's URL is http://localhost:5000

The web app has three publicly visible pages:
(1)     Welcome Page
(2)     Sign Up Page - this was not included in the requirements but I wrote it
as a convenience, since adding users by hand got tedious.
(3)     Log In Page - non-admin users can see it but aren't allowed to log in.

The username & password of the admin user is admin/admin.
The admin user can log in.  Logging in takes the user to a search screen.
The SQLIte database is prepopulated with ten of the worst movies of all time.
A search on some or all of these events results in a display of the following:
        event ID
        event name
        customer name
        customer email address
        number of tickets currently held by the customer.

Per Instructions, a REST API is provided and consists of the following functions:
        purchase: allows a user to purchase up to an infinite number of tickets
        cancel: allows a user to cancel up to the number of previously purchased tickets
        eschange: allows the user to exchange up to the number of previously purchased
                  tickets for tickets to another event.

The URLs for the API are:

        http://localhost:5000/purchase/<customer>/<number of tix>/<event id>
        http://localhost:5000/cancel/<customer>/<number of tix/<event id>
        http://localhost:5000/exchange/<customer>/number of tix/<old event id>/<new event id>

