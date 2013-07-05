-- This file will create a brand new piwik.db file with the appropriate tables and collumns;
-- Call this file from the command line using the following syntax;
-- sqlite piwik.db piwikSkipCreate.sql;

drop table if exists skip;
drop table if exists logs;
create table skip(profile, site_id,log_file,last_line,tot_lines);
create table logs(profile, site_id,date_time,processed,time);

-- End of File
