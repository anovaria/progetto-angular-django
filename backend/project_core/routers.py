class GoldReportRouter:
    """
    Tutti i modelli dell'app goldreport_mssql vanno sul DB 'goldreport'.
    Il DB Gold è di produzione: NON si scrive e NON si migra.
    """
    route_app_labels = {'goldreport_mssql'}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return 'goldreport'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return 'goldreport'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if (
            obj1._meta.app_label in self.route_app_labels or
            obj2._meta.app_label in self.route_app_labels
        ):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Mai e poi mai toccare un DB di produzione
        if app_label in self.route_app_labels:
            return False
        return None


class ImportelabRouter:
    """
    I modelli di importelab vanno sul DB 'default' (MSSQL DjangoIntranet).
    """
    route_app_labels = {'importelab'}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return 'default'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return 'default'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if (
            obj1._meta.app_label in self.route_app_labels or
            obj2._meta.app_label in self.route_app_labels
        ):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.route_app_labels:
            return db == 'default'
        return None