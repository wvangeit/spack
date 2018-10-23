uid="`id -u`"
if [ "$uid" '=' '0' ] ; then
    for key_type in dsa ecdsa ed25519 rsa ; do
        private_key_file="/etc/ssh/ssh_host_${key_type}_key"
        public_key_file="$private_key_file.pub"

        if [ '!' -f "$private_key_file" ] ; then
            ssh-keygen \
                -q -t "$key_type" -N "" -f "$private_key_file"
            chmod 600 "$private_key_file"
            chmod 644 "$public_key_file"
        fi
    done

    mkdir -p /var/run/sshd

    pgrep -u 0 -U 0 sshd &> /dev/null
    if [ '!' "$?" '=' '0' ] ; then
        nohup /usr/sbin/sshd -f /etc/ssh/sshd_config < /dev/null &> /dev/null
    fi
fi

if [ '!' -f "$HOME/.ssh/id_rsa" ] ; then
    ssh-keygen \
        -t rsa -C "spack.developer@docker.host" -N "" -f "$HOME/.ssh/id_rsa"
    cat "$HOME/.ssh/id_rsa.pub" >> "$HOME/.ssh/authorized_keys"
    chmod 600 "$HOME/.ssh/authorized_keys"

    docker_ip="`ip address show dev eth0 |
                grep inet |
                cut -d' ' -f 6 |
                cut -d/ -f 1`"

    ssh-keyscan -t rsa 127.0.0.1 localhost "$docker_ip" "`hostname`" \
        > "$HOME/.ssh/known_hosts" 2> /dev/null
fi
