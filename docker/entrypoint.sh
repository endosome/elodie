#!/bin/sh
# Runs elodie in the Docker image and warns about options which are easy to
# forget, see "Running in Docker" in the Readme.

directory="${ELODIE_APPLICATION_DIRECTORY:-/elodie}"

case "$1" in
    import|update|generate-db|verify|batch)
        case " $* " in
            *" --help "*) ;;
            *)
                if ! awk -v d="$directory" '$5 == d { found = 1 } END { exit !found }' /proc/self/mountinfo; then
                    echo "Warning: $directory is not mounted. The hash database is lost when the container is removed and files which were imported before are not found as duplicates. Mount a folder, i.e. -v ~/.elodie:$directory" >&2
                fi
                if [ -z "$TZ" ] && { [ "$1" = import ] || [ "$1" = update ]; }; then
                    echo "Warning: TZ is not set, UTC is used for dates which come from the time of a file or are stored in UTC (videos without a GPS position). Set your time zone, i.e. -e TZ=Europe/Warsaw" >&2
                fi
                ;;
        esac
        ;;
esac

# exec so elodie gets the signals, i.e. SIGTERM of docker stop
exec python /opt/elodie/elodie.py "$@"
