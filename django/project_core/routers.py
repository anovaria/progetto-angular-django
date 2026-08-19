class GoldReportRouter:
    """
    Tutti i modelli dell'app goldreport_mssql vanno sul DB 'goldreport'.
    Anche tabelle specifiche come shared.fornitori vanno su goldreport.
    Il DB Gold è di produzione: NON si scrive e NON si migra.
    """
    route_app_labels = {'goldreport_mssql'}
    
    # Tabelle specifiche da leggere su goldreport (anche se in altre app)
    goldreport_tables = {'TFornitori', 'v_masterdata', 't_t_ean1','v_RicevimentiGoldArtFo'}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return 'goldreport'
        if model._meta.db_table in self.goldreport_tables:
            return 'goldreport'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return 'goldreport'
        # Blocca scritture su tabelle goldreport da altre app
        if model._meta.db_table in self.goldreport_tables:
            return 'goldreport'  # Gold è read-only, fallirà se tentano scrittura
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Permetti relazioni cross-database per fornitori
        db1 = self._get_db(obj1)
        db2 = self._get_db(obj2)
        if db1 and db2:
            return True
        if obj1._meta.app_label in self.route_app_labels or obj2._meta.app_label in self.route_app_labels:
            return True
        if obj1._meta.db_table in self.goldreport_tables or obj2._meta.db_table in self.goldreport_tables:
            return True
        return None
    
    def _get_db(self, obj):
        if obj._meta.app_label in self.route_app_labels:
            return 'goldreport'
        if obj._meta.db_table in self.goldreport_tables:
            return 'goldreport'
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Mai e poi mai toccare un DB di produzione
        if app_label in self.route_app_labels:
            return False
        return None


class CursoriRouter:
    """
    I modelli di cursori vanno sul DB 'default' (DjangoIntranet).
    Le tabelle fisiche stanno nello schema [cursori] creato manualmente.
    """
    route_app_labels = {'cursori'}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return 'default'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return 'default'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if (obj1._meta.app_label in self.route_app_labels or
                obj2._meta.app_label in self.route_app_labels):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.route_app_labels:
            return db == 'default'
        return None


class CategoryRouter:
    """
    Db_Category — sola lettura, nessuna migrazione.
    Usato da cursori/services.py via connections['category'].
    """
    def db_for_read(self, model, **hints):
        return None

    def db_for_write(self, model, **hints):
        return None

    def allow_relation(self, obj1, obj2, **hints):
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == 'category':
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