# MediQueue – DevOps Case Study & Ansible Automation (IA Activity 1)

MediQueue is a hospital appointment booking system. Patients book a slot in a
department, and staff see the upcoming appointments. This repository holds the
**Ansible configuration management** that builds a full 3-tier MediQueue
server from a blank Ubuntu EC2 instance:

```
Browser ──HTTP:80──▶ Nginx (reverse proxy) ──:8000──▶ Gunicorn + Flask app ──:5432──▶ PostgreSQL
            [web]                                         [app]                          [db]
```

## Project layout

```
ansible.cfg                       # defaults: inventory, roles path, sudo
site.yml                          # main playbook – 5 plays (common, db, app, web, verify)
group_vars/all.yml                # app, DB, web and OS variables
inventories/
  single-node/hosts.ini           # one EC2 box plays web+app+db (used for the demo)
  single-node/group_vars/all.yml
  multi-node/hosts.ini            # web01, app01, app02, db01 on separate EC2 instances
  multi-node/group_vars/all.yml
roles/
  common/    # apt update, base packages, timezone, app user, UFW firewall
  postgres/  # install PostgreSQL, create DB + user, remote access for multi-node
  app/       # Flask code, virtualenv, .env, systemd unit for Gunicorn
  nginx/     # reverse-proxy site with load-balanced upstream, /health route
```

## How to run (on the EC2 instance)

```bash
sudo apt update && sudo apt install -y ansible
cd IA1-MediQueue-Ansible
ansible-inventory --graph                  # show groups/hosts
ansible all -m ping                        # connectivity
ansible-playbook site.yml --syntax-check   # syntax
ansible-playbook site.yml --check          # dry run (first run may stop early, packages aren't installed yet)
ansible-playbook site.yml                  # deploy
ansible-playbook site.yml                  # run again → changed=0 (idempotent)
curl http://localhost/health
```

Then open `http://<EC2-public-IP>/` in a browser (security group must allow port 80).

Run only one tier with tags: `ansible-playbook site.yml --tags db` (`common`, `db`, `app`, `web`, `verify`).

Multi-node: fill in the private IPs in `inventories/multi-node/hosts.ini`, then
`ansible-playbook -i inventories/multi-node/hosts.ini site.yml`.

## Endpoints

| URL | Purpose |
|---|---|
| `/` | Booking form + list of appointments |
| `POST /book` | Create appointment |
| `/api/appointments` | JSON list |
| `/health` | `{"status":"UP","database":"connected",...}` used by the smoke test |
