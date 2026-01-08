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
      sql    := regexp_replace(record.prosrc,    concat('\m', record.oldschema, '\M'), newschema, 'g');
      config := regexp_replace(record.proconfig, concat('\m', record.oldschema, '\M'), newschema, 'g');
      CONTINUE WHEN sql IS NOT DISTINCT FROM record.prosrc AND
                 config IS NOT DISTINCT FROM record.proconfig;
      UPDATE pg_proc SET prosrc = sql, proconfig = config WHERE oid = record.oid;
    END LOOP;

    -- rename schema name in rmb_internal_index.def
    FOR record IN
      SELECT schemaname AS oldschema FROM pg_tables
      WHERE schemaname ~ regexp AND tablename = 'rmb_internal_index'
    LOOP
      newschema := regexp_replace(record.oldschema, concat('^', oldtenant), newtenant);
      EXECUTE format('UPDATE %I.rmb_internal_index SET def = replace(def, %L, %L)',
                     record.oldschema,
                     concat(' ', record.oldschema, '.'),
                     concat(' ', newschema, '.'));
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

    -- rename tenant name in mod_search consortium_instance.tenant_id
    FOR record IN
      SELECT schemaname AS oldschema FROM pg_tables
      WHERE schemaname = concat(oldtenant, '_mod_search') AND tablename = 'instance_classification'
    LOOP
      EXECUTE format('UPDATE %I.instance_classification SET tenant_id = %L WHERE tenant_id = %L',
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
