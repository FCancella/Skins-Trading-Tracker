# Counter‑Strike Skin Portfolio Management

This Django project provides a simple, responsive web interface for
tracking Counter‑Strike skin trades. It lets users record purchases,
optionally record sale information at a later date, and view a summary
of realised profits and holding periods. The layout uses Bootstrap
cards and tables to organise the information clearly on a single page.

## Features

* **Add new trades** with an item name, buy price, buy source and
  buy date (defaults to the current date). Allowed sources are
  Youpin, Skinport, Floatdb, Dash BOT and Dash P2P.
* **Inline sell form** for each open trade. When a trade is sold you
  can enter the sell price, sell source and sold date directly in the
  portfolio table. PnL and holding days are computed automatically.
* **Portfolio summary** displays the total number of items, the number
  of open and closed positions, the total realised PnL and the average
  holding days for closed trades.
* **Admin interface** included via Django’s admin site to manage trades
  in bulk if desired.

## Setup

1. **Install dependencies:** You need Django 4.x or newer. In a Python
   virtual environment run:

   ```sh
   pip install django
   ```

2. **Apply migrations:** From the project root run:

   ```sh
   python manage.py migrate
   ```

3. **Run the development server:**

   ```sh
   python manage.py runserver
   ```

4. **Open the app:** Navigate to `http://127.0.0.1:8000/` in your
   browser. You should see the portfolio dashboard with the summary,
   add trade form and the trades table.

5. **Admin site (optional):** To enable the admin interface, create a
   superuser with `python manage.py createsuperuser` and then visit
   `http://127.0.0.1:8000/admin/`.

## Notes

This code was generated in an environment without access to the
internet, so the Django framework itself was not installed or tested
here. Please ensure you install Django in your own environment before
running the application. All business logic, templates and models
should function as described once Django is available.