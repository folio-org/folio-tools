CREATE OR REPLACE PROCEDURE tenant_rename(oldtenant text, newtenant text) AS
$PROCEDURE$
  DECLARE
    regexp text := concat('^', oldtenant, '_(mod|mgr)_');
    record RECORD;
    newschema text;
    sql text;
    config text;
  BEGIN
    -- reject characters that require masking in regexp or start with digit
    -- tenant starting with digit is invalid schema name in PostgreSQL
    IF oldtenant !~ '^[\w_][\w\d_]*$' THEN
      RAISE 'Invalid character in oldtenant: %', oldtenant;
    END IF;
    IF newtenant !~ '^[\w_][\w\d_]*$' THEN
      RAISE 'Invalid character in newtenant: %', newtenant;
    END IF;

    -- exclusive write lock on all tables
    RAISE INFO 'Waiting for write locks ...';
    FOR record IN
      SELECT schemaname, tablename FROM pg_tables WHERE schemaname ~ regexp
    LOOP
      EXECUTE format('LOCK TABLE %I.%I IN EXCLUSIVE MODE', record.schemaname, record.tablename);
    END LOOP;
    RAISE INFO 'Holding all write locks.';

    -- rename each role and change role password
    FOR record IN
      SELECT rolname AS oldschema FROM pg_roles WHERE rolname ~ regexp
    LOOP
      newschema := regexp_replace(record.oldschema, concat('^', oldtenant), newtenant);
      EXECUTE format('ALTER ROLE %I RENAME TO %I', record.oldschema, newschema);
      EXECUTE format('ALTER ROLE %I SET search_path TO %I', newschema, newschema);
      EXECUTE format('ALTER ROLE %I PASSWORD %L', newschema, newtenant);
    END LOOP;

    -- rename schema name in source code and config (eg. {search_path=diku_mod_foo}) of functions and procedures
    FOR record IN
      SELECT pg_proc.oid, nspname AS oldschema, prosrc, proconfig FROM pg_proc, pg_namespace
      WHERE pronamespace = pg_namespace.oid AND nspname ~ regexp
    LOOP
      newschema := regexp_replace(record.oldschema, concat('^', oldtenant), newtenant);
      -- \m and \M match at begin and end of a word, word = [a-zA-Z0-9_]+
      sql := regexp_replace(record.prosrc, concat('\m', record.oldschema, '\M'), newschema, 'g');
      -- https://github.com/folio-org/mod-data-export/blob/v5.3.0/src/main/resources/db/changelog/changes/slice_instances_all_ids.sql#L8
      -- https://github.com/folio-org/mod-data-export/blob/v5.3.0/src/main/resources/db/changelog/changes/slice_holdings_all_ids.sql#L8
      sql := replace(sql, concat(' ', oldtenant, '_mod_inventory_storage.'),
                          concat(' ', newtenant, '_mod_inventory_storage.') );
      IF pg_typeof(record.proconfig) = 'text[]'::regtype THEN
        config := regexp_replace(record.proconfig[1], concat('\m', record.oldschema, '\M'), newschema, 'g');
        CONTINUE WHEN sql IS NOT DISTINCT FROM record.prosrc AND
                   config IS NOT DISTINCT FROM record.proconfig[1];
        UPDATE pg_proc SET prosrc = sql, proconfig[1] = config WHERE oid = record.oid;
      ELSE
        config := regexp_replace(record.proconfig, concat('\m', record.oldschema, '\M'), newschema, 'g');
        CONTINUE WHEN sql IS NOT DISTINCT FROM record.prosrc AND
                   config IS NOT DISTINCT FROM record.proconfig;
        UPDATE pg_proc SET prosrc = sql, proconfig = config WHERE oid = record.oid;
      END IF;
    END LOOP;

    -- rename schema name in rmb_internal_index.def
    -- https://github.com/folio-org/mod-circulation-storage/blob/v17.4.0/src/main/resources/templates/db_scripts/index_dateLostItemShouldBeBilled.sql#L10
    FOR record IN
      SELECT schemaname AS oldschema FROM pg_tables
      WHERE schemaname ~ regexp AND tablename = 'rmb_internal_index'
    LOOP
      newschema := regexp_replace(record.oldschema, concat('^', oldtenant), newtenant);
      EXECUTE format('UPDATE %I.rmb_internal_index SET def = replace(replace(def, %L, %L), %L, %L)',
                     record.oldschema,
                     concat(' ', record.oldschema, '.'),
                     concat(' ', newschema, '.'),
                     concat('(', record.oldschema, '.'),
                     concat('(', newschema, '.'));
    END LOOP;

    -- rename schema name in rmb_job.jsonb->>'tenant'
    FOR record IN
      SELECT schemaname AS oldschema FROM pg_tables
      WHERE schemaname ~ regexp AND tablename = 'rmb_job'
    LOOP
      EXECUTE format($$ UPDATE %I.rmb_job
                        SET jsonb = jsonb_set(jsonb, '{tenant}', to_jsonb(%L::text))
                        WHERE jsonb->>'tenant' = %L $$,
                     record.oldschema, newtenant, oldtenant);
    END LOOP;

    -- delete wrong md5sum in the `databasechangelog` liquibase table
    -- liquibase will replace it with the new md5sum on next run
    FOR record IN
      SELECT schemaname AS oldschema FROM pg_tables
      WHERE schemaname ~ regexp AND tablename = 'databasechangelog'
    LOOP
      EXECUTE format('UPDATE %I.databasechangelog SET md5sum = NULL', record.oldschema);
    END LOOP;

    -- rename tenant name in mod_agreements log_entry_additional_info
    FOR record IN
      SELECT schemaname AS oldschema FROM pg_tables
      WHERE schemaname = concat(oldtenant, '_mod_agreements') AND tablename = 'log_entry_additional_info'
    LOOP
      EXECUTE format($$ UPDATE %I.log_entry_additional_info
                        SET additional_info_elt = %L
                        WHERE additional_info_idx = 'tenantId' AND additional_info_elt = %L $$,
                     record.oldschema, concat(newtenant, '_mod_agreements'), concat(oldtenant, '_mod_agreements'));
      EXECUTE format($$ UPDATE %I.log_entry_additional_info
                        SET additional_info_elt = %L
                        WHERE additional_info_idx IN ('tenant', '{tenant}') AND additional_info_elt = %L $$,
                     record.oldschema, newtenant, oldtenant);
    END LOOP;

    -- rename tenant name in mod_fqm_manager entity_type_definition
    FOR record IN
      SELECT schemaname AS oldschema FROM pg_tables
      WHERE schemaname = concat(oldtenant, '_mod_fqm_manager') AND tablename = 'entity_type_definition'
    LOOP
      EXECUTE format($$ UPDATE %I.entity_type_definition SET definition = regexp_replace(definition::text, %L, %L, 'g')::json $$,
                     record.oldschema,
                     concat('\m', oldtenant, '_mod_'),
                     concat(newtenant, '_mod_'));
    END LOOP;

    -- rename tenant name in mod_pubsub audit_message.tenant_id
    FOR record IN
      SELECT schemaname AS oldschema FROM pg_tables
      WHERE schemaname = concat(oldtenant, '_mod_pubsub') AND tablename = 'audit_message'
    LOOP
      EXECUTE format('UPDATE %I.audit_message SET tenant_id = %L WHERE tenant_id = %L',
                     record.oldschema, newtenant, oldtenant);
    END LOOP;

    -- rename tenant name in mod_search consortium_instance.tenant_id
    FOR record IN
      SELECT schemaname AS oldschema FROM pg_tables
      WHERE schemaname = concat(oldtenant, '_mod_search') AND tablename = 'consortium_instance'
    LOOP
      EXECUTE format('UPDATE %I.consortium_instance SET tenant_id = %L WHERE tenant_id = %L',
                     record.oldschema, newtenant, oldtenant);
    END LOOP;

    -- rename tenant name in mod_search holding.tenant_id
    FOR record IN
      SELECT schemaname AS oldschema FROM pg_tables
      WHERE schemaname = concat(oldtenant, '_mod_search') AND tablename = 'holding'
    LOOP
      EXECUTE format('UPDATE %I.holding SET tenant_id = %L WHERE tenant_id = %L',
                     record.oldschema, newtenant, oldtenant);
    END LOOP;

    -- rename tenant name in mod_search instance.tenant_id
    FOR record IN
      SELECT schemaname AS oldschema FROM pg_tables
      WHERE schemaname = concat(oldtenant, '_mod_search') AND tablename = 'instance'
    LOOP
      EXECUTE format('UPDATE %I.instance SET tenant_id = %L WHERE tenant_id = %L',
                     record.oldschema, newtenant, oldtenant);
    END LOOP;

    -- rename tenant name in mod_search instance_classification.tenant_id
    FOR record IN
      SELECT schemaname AS oldschema FROM pg_tables
      WHERE schemaname = concat(oldtenant, '_mod_search') AND tablename = 'instance_classification'
    LOOP
      EXECUTE format('UPDATE %I.instance_classification SET tenant_id = %L WHERE tenant_id = %L',
                     record.oldschema, newtenant, oldtenant);
    END LOOP;

    -- rename tenant name in mod_search merge_range.tenant_id
    FOR record IN
      SELECT schemaname AS oldschema FROM pg_tables
      WHERE schemaname = concat(oldtenant, '_mod_search') AND tablename = 'merge_range'
    LOOP
      EXECUTE format('UPDATE %I.merge_range SET tenant_id = %L WHERE tenant_id = %L',
                     record.oldschema, newtenant, oldtenant);
    END LOOP;

    -- rename tenant name in mod_source_record_manager journal_records.tenant_id
    FOR record IN
      SELECT schemaname AS oldschema FROM pg_tables
      WHERE schemaname = concat(oldtenant, '_mod_source_record_manager') AND tablename = 'journal_records'
    LOOP
      EXECUTE format('UPDATE %I.journal_records SET tenant_id = %L WHERE tenant_id = %L',
                     record.oldschema, newtenant, oldtenant);
    END LOOP;

    -- rename schemata
    FOR record IN
      SELECT schema_name AS oldschema FROM information_schema.schemata WHERE schema_name ~ regexp
    LOOP
      newschema := regexp_replace(record.oldschema, concat('^', oldtenant), newtenant);
      EXECUTE format('ALTER SCHEMA %I RENAME TO %I', record.oldschema, newschema);
    END LOOP;

    -- rename tenant in column mod_agreements__system.known_tenant.at_name
    BEGIN
      UPDATE mod_agreements__system.known_tenant SET at_name = newtenant WHERE at_name = oldtenant;
    EXCEPTION
      -- ignore if schema or table doesn't exist
      WHEN OTHERS THEN NULL;
    END;

    RAISE INFO 'Renames completed.';
  END;
$PROCEDURE$ LANGUAGE plpgsql;
