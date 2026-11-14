#!/usr/bin/env python3
"""Figures for the article "Ansible explained without the jargon": one editable .drawio file per figure and a matching SVG.

Reuses the layout, palette and draw.io writer of the RoboShop AI series (sites/jithendar.com/docs/knowledge-sharing/roboshop-ai/diagrams).
Run from www/. The SVG is rendered here, not exported by draw.io: if a .drawio file is edited in draw.io, re-export it
over the SVG. PNG copies: render_png.py (Playwright + Chromium).
Facts follow github.com/mrjithendar/Ansible at 29ea7b1 (roboshop.yml, roles/, inventory/aws_ec2.yml, group_vars/,
ansible.cfg, Jenkinsfile).
"""
import importlib.util
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[3] / "public" / "images" / "ansible-roboshop"
spec = importlib.util.spec_from_file_location("series_diagrams", HERE.parents[1] / "roboshop-ai" / "diagrams" / "build_diagrams.py")
series = importlib.util.module_from_spec(spec)
sys.modules["series_diagrams"] = series
spec.loader.exec_module(series)
Page = series.Page

SERVERS = [("frontend", "the website (nginx)"), ("catalogue", "product list (Node.js)"), ("user", "logins (Node.js)"),
           ("cart", "shopping basket (Node.js)"), ("shipping", "delivery costs (Java)"), ("payment", "card payments (Python)"),
           ("mongodb", "products and users database"), ("rabbitmq", "message queue")]


def big_picture():
    p = Page("01-big-picture", "The big picture", 720, 420, "One machine gives instructions, many servers follow them",
             "A person, or the Jenkins build server, runs one command on a control machine. Ansible reads the written instructions in "
             "this repository and connects to each of the eight RoboShop servers on AWS over SSH: frontend, catalogue, user, cart, "
             "shipping, payment, mongodb and rabbitmq. Nothing extra is installed on the servers; they only need SSH and Python.")
    p.zone("Control machine", 15, 12, 250, 396)
    p.zone("Eight RoboShop servers on AWS", 290, 12, 415, 396)
    p.node("you", "browser", 30, 44, 220, 56, "You, or Jenkins", "types one command")
    p.node("ansible", "gateway", 30, 170, 220, 72, "Ansible", "reads the instructions,", "then does the work")
    p.node("repo", "store", 30, 296, 220, 56, "This repository", "the written instructions")
    p.note(30, 364, "No agent on the servers:\njust SSH and Python.", 12, "#475569", True)
    p.edge("you", "ansible", label="runs")
    p.edge("repo", "ansible", a_side="t", b_side="b", label="reads")
    for i, (name, line) in enumerate(SERVERS):
        y = 40 + i * 45
        p.node(name, "service", 470, y, 220, 40, name, line)
        p.edge("ansible", name, a_side="r", b_side="l", a_at=0.15 + i * 0.1, label="SSH" if i == 3 else "", dx=-40)
    return p


def building_blocks():
    p = Page("02-building-blocks", "Building blocks", 720, 540, "How the pieces of Ansible fit inside each other",
             "The inventory is the address book: which servers exist and what job each one has. The playbook, roboshop.yml, is the run "
             "sheet. It holds plays; each play picks a group of servers from the inventory and gives them roles. A role, such as catalogue, "
             "is a recipe card made of tasks. Each task uses one module, a ready-made tool such as dnf to install software or copy to put "
             "a file in place. A handler runs only when a task changed something. Variables fill in the blanks, and secrets come from an "
             "encrypted vault file.")
    p.zone("Who", 15, 12, 200, 516)
    p.node("inv", "store", 30, 44, 170, 92, "Inventory", "the address book:", "which servers exist,", "grouped by job")
    p.node("vars", "mcp", 30, 300, 170, 76, "Variables", "fill in the blanks:", "names, folders, versions")
    p.node("vault", "bus", 30, 400, 170, 76, "Vault", "secrets, locked with", "a password")
    p.zone("Playbook roboshop.yml: the run sheet", 230, 12, 475, 516)
    p.zone("Play: \"Application tier\" (hosts: catalogue, user, cart, ...)", 245, 40, 445, 474)
    p.zone("Role: catalogue (a recipe card)", 260, 70, 415, 430)
    p.node("t1", "gateway", 275, 100, 345, 52, "Task: install Node.js", "module: dnf (the software installer)")
    p.node("t2", "gateway", 275, 172, 345, 52, "Task: copy the app's files", "module: copy")
    p.node("t3", "gateway", 275, 244, 345, 52, "Task: write the service settings", "module: template (fill-in-the-blanks file)")
    p.node("t4", "gateway", 275, 316, 345, 52, "Task: start catalogue", "module: systemd_service")
    p.node("h1", "bus", 275, 408, 345, 72, "Handler: restart catalogue", "runs once, at the end,", "only if a task above changed something")
    p.edge("inv", "t1", a_side="r", b_side="l", via=[(222, 90), (222, 126)], label="hosts:", dy=-12, t=0.6)
    p.edge("t1", "t2")
    p.edge("t2", "t3")
    p.edge("t3", "t4")
    p.edge("t3", "h1", kind="async", a_side="r", b_side="r", a_at=0.5, b_at=0.5, via=[(648, 270), (648, 444)], label="notify")
    p.edge("vars", "t3", kind="dashed", a_side="r", b_side="l", via=[(240, 338), (240, 270)])
    p.edge("vault", "vars", kind="dashed", a_side="t", b_side="b")
    return p


def repo_map():
    p = Page("03-repo-map", "Repository map", 720, 470, "What each folder of the Ansible repository holds",
             "roboshop.yml is the main playbook. roles holds one folder per component plus common. inventory holds the dynamic AWS "
             "inventory and a static example. group_vars holds settings shared by every server and the encrypted vault. ansible.cfg "
             "sets defaults such as the SSH user and the key file. requirements.yml lists the extra module collections. terraform builds "
             "the servers. The Jenkinsfile runs everything. examples holds beginner playbooks and extras holds reference roles that are "
             "not deployed.")
    rows = [
        (("play", "gateway", "roboshop.yml", "the main playbook: the run sheet", "data tier, then apps, then the website"),
         ("roles", "service", "roles/", "one recipe card per component", "plus common: the shared first steps")),
        (("inv", "store", "inventory/", "aws_ec2.yml: asks AWS for the server list", "hosts.example.ini: a hand-written list"),
         ("gv", "mcp", "group_vars/all/", "main.yml: settings every server shares", "vault.yml: the secrets, encrypted")),
        (("cfg", "external", "ansible.cfg", "defaults: log in as rocky with roboshop.pem,", "use sudo, speed up SSH"),
         ("req", "external", "requirements.yml", "extra toolkits to download first:", "AWS, MySQL, RabbitMQ and more")),
        (("tf", "agent", "terraform/", "builds the servers, network and databases", "(the subject of its own article)"),
         ("jf", "browser", "Jenkinsfile", "the push-button pipeline:", "plan, build, deploy or delete")),
        (("ex", "absent", "examples/basics/", "eight small practice playbooks", "for learning, not for the shop"),
         ("extras", "absent", "extras/", "older roles kept for reference:", "Jenkins, Docker, ELK, Prometheus")),
    ]
    for r, pair in enumerate(rows):
        for c, (id, kind, title, *lines) in enumerate(pair):
            p.node(id, kind, 15 + c * 355, 12 + r * 92, 335, 76, title, *lines)
    return p


def inventory():
    p = Page("04-inventory", "Dynamic inventory", 720, 450, "How Ansible finds the servers without a hand-written list",
             "Terraform creates one server per component and labels each one with tags such as Project = roboshop and Component = cart. "
             "The dynamic inventory file inventory/aws_ec2.yml asks AWS for every running server tagged Project = roboshop and turns "
             "each Component tag into a group. The cart group then gets the application-tier play, which applies the cart role.")
    p.node("tf", "agent", 15, 30, 210, 88, "Terraform", "creates the servers and", "labels each one:", "Component = cart")
    p.node("aws", "external", 255, 30, 210, 88, "AWS EC2", "8 running servers,", "each with a Project", "and a Component tag")
    p.node("plug", "store", 495, 30, 210, 88, "inventory/aws_ec2.yml", "asks AWS: running,", "Project = roboshop?", "groups by Component")
    p.edge("tf", "aws", a_side="r", b_side="l", label="builds")
    p.edge("aws", "plug", a_side="r", b_side="l", label="the list", both=True)
    p.zone("Groups Ansible now knows about", 15, 160, 690, 128)
    names = ["frontend", "catalogue", "user", "shipping", "payment", "mongodb", "rabbitmq", "cart"]
    for i, name in enumerate(names):
        x, y = 30 + (i % 4) * 168, 188 + (i // 4) * 48
        p.node(f"g{name}", "service" if name != "cart" else "bus", x, y, 156, 38, name)
    p.edge("plug", "gshipping", a_at=(612 - 495) / 210, label="one group per tag", dx=0)
    p.node("play", "gateway", 15, 330, 330, 80, "Play: \"Application tier\"", "hosts: catalogue, user, cart,", "shipping, payment")
    p.node("role", "service", 375, 330, 330, 80, "Role: cart", "install Node.js, copy the code,", "start the cart service")
    p.edge("gcart", "play", kind="async", via=[(612, 306), (180, 306)], label="the cart server joins this play", t=0.1)
    p.edge("play", "role", a_side="r", b_side="l", label="applies")
    return p


def play_order():
    p = Page("05-play-order", "Order of the run", 720, 500, "The playbook runs in four steps, so nothing starts before what it needs",
             "Step one checks every server: is it a known component, does it answer, and which group is it in. Step two sets up the data "
             "tier: MongoDB and RabbitMQ. Aurora MySQL and Redis are managed by AWS and built by Terraform, so Ansible only loads data into "
             "them. Step three sets up the five application services. Step four sets up the frontend website, which forwards requests to "
             "the services.")
    p.zone("Step 1 · every server", 15, 12, 690, 88)
    p.node("pre", "external", 30, 36, 660, 52, "Check in", "Is it a known component? Wait until it answers. Put it in its group.")
    p.zone("Step 2 · data tier", 15, 112, 690, 110)
    p.node("mongo", "store", 30, 140, 210, 64, "mongodb", "database for products", "and user accounts")
    p.node("rabbit", "store", 255, 140, 210, 64, "rabbitmq", "message queue for", "payments and orders")
    p.node("managed", "absent", 480, 140, 210, 64, "Aurora MySQL + Redis", "managed by AWS,", "built by Terraform")
    p.zone("Step 3 · application tier", 15, 234, 690, 110)
    apps = [("catalogue", "Node.js", "products"), ("user", "Node.js", "logins"), ("cart", "Node.js", "basket"),
            ("shipping", "Java", "delivery cost"), ("payment", "Python", "card payments")]
    for i, (name, lang, job) in enumerate(apps):
        p.node(name, "service", 30 + i * 132, 262, 126, 64, name, lang, job)
    p.zone("Step 4 · web tier", 15, 356, 690, 88)
    p.node("frontend", "gateway", 30, 380, 660, 52, "frontend · nginx", "The website customers open. It forwards /api/... requests to the five services.")
    p.edge("pre", "rabbit", b_at=0.5, a_at=(360 - 30) / 660)
    p.edge("rabbit", "cart", a_at=0.5, b_at=(360 - 294) / 126)
    p.edge("cart", "frontend", a_at=(360 - 294) / 126, b_at=0.5)
    p.note(30, 456, "Each step finishes on every server before the next one begins.", 12, "#475569", True)
    return p


def role_anatomy():
    p = Page("06-role-anatomy", "Inside a role", 720, 470, "Inside one role: the catalogue recipe card and what it produces",
             "The catalogue role is a folder. meta says the common role runs first, which creates the roboshop user and its folders. "
             "defaults says where the app lives. tasks lists the steps in order: install Node.js, copy the code, install dependencies, "
             "write the service file, start it. files holds the app's code. templates holds the service file with blanks for the folder "
             "and the database address. handlers restarts the service, but only if something changed.")
    p.zone("roles/catalogue/ (in Git)", 15, 12, 330, 446)
    p.zone("The catalogue server after a run", 375, 12, 330, 446)
    left = [("meta", "meta/", "needs the common role first"), ("defaults", "defaults/", "where the app lives"),
            ("tasks", "tasks/", "the steps, in order"), ("files", "files/", "the app's code: server.js"),
            ("tmpl", "templates/", "service file with blanks"), ("hand", "handlers/", "restart, only if needed")]
    for i, (id, title, line) in enumerate(left):
        p.node(id, "gateway" if id != "hand" else "bus", 30, 40 + i * 68, 300, 56, title, line)
    right = [("user", 0, "service", "roboshop user and folders", "a locked-down account to run as"),
             ("node", 2, "service", "Node.js 20 installed", "plus the app's npm packages"),
             ("code", 3, "store", "/opt/roboshop/catalogue/", "server.js and package.json"),
             ("unit", 4, "store", "catalogue.service", "MONGO_URL filled in"),
             ("run", 5, "service", "catalogue running", "restarted if a file changed")]
    for id, row, kind, title, line in right:
        p.node(id, kind, 390, 40 + row * 68, 300, 56, title, line)
    for a, b in (("meta", "user"), ("tasks", "node"), ("files", "code"), ("tmpl", "unit"), ("hand", "run")):
        p.edge(a, b, a_side="r", b_side="l")
    return p


def idempotency():
    p = Page("07-idempotency", "Safe to repeat", 720, 420, "Run it once, twice or after a mistake: the result is the same",
             "On a brand-new server every frontend task changes something: nginx is installed, the web pages and settings are copied, "
             "and nginx is started. Run the same playbook again and every task reports ok, because the server already matches. If someone "
             "edits the proxy settings by hand, the next run changes only that file back and reloads nginx.")
    cols = [("First run: a new server", ["store"] * 4, ["changed: installed", "changed: copied", "changed: copied", "changed: started"],
             "4 changed", "bus"),
            ("Second run: nothing to do", ["service"] * 4, ["ok: already there", "ok: same files", "ok: same file", "ok: running"],
             "0 changed", "service"),
            ("After a hand edit", ["service", "service", "store", "service"], ["ok", "ok", "changed: put back", "ok: then reloaded"],
             "1 changed", "bus")]
    tasks = ["Install nginx", "Copy the web pages", "Copy the proxy settings", "Start nginx"]
    for c, (label, kinds, results, total, tkind) in enumerate(cols):
        x = 15 + c * 235
        p.zone(label, x, 12, 220, 396)
        for r, (task, kind, result) in enumerate(zip(tasks, kinds, results)):
            p.node(f"c{c}r{r}", kind, x + 12, 40 + r * 70, 196, 52, task, result)
            if r:
                p.edge(f"c{c}r{r - 1}", f"c{c}r{r}")
        p.node(f"c{c}t", tkind, x + 12, 330, 196, 52, "Summary", total)
        p.edge(f"c{c}r3", f"c{c}t")
    return p


def handlers():
    p = Page("08-handlers", "Handlers", 720, 380, "Restart only when something changed",
             "A task copies the nginx settings and notifies the handler named Reload nginx. If the file was already the same, nothing "
             "happens. If it changed, the handler waits until the end of the play, checks the whole configuration with nginx -t, and only "
             "then reloads nginx. A broken file stops the run before it reaches the live website.")
    p.node("copy", "gateway", 15, 30, 210, 72, "Task: copy settings", "template: roboshop.conf", "notify: Reload nginx")
    p.node("q", "external", 255, 30, 210, 72, "Did the file change?", "Ansible compares it", "with what is there")
    p.node("no", "service", 495, 30, 210, 72, "No: nothing to do", "nginx keeps running,", "no restart, no blip")
    p.node("wait", "bus", 255, 160, 210, 72, "Yes: handler queued", "waits until every task", "in the play is done")
    p.node("check", "store", 255, 270, 210, 72, "Check: nginx -t", "is the whole config valid?", "if not, stop here")
    p.node("reload", "service", 495, 270, 210, 72, "Reload nginx", "new settings live,", "visitors not cut off")
    p.node("stop", "reject", 15, 270, 210, 72, "Run stops", "the live site keeps", "the old, working config")
    p.edge("copy", "q", a_side="r", b_side="l")
    p.edge("q", "no", a_side="r", b_side="l", label="no", dy=-14)
    p.edge("q", "wait", label="yes")
    p.edge("wait", "check")
    p.edge("check", "reload", a_side="r", b_side="l", label="valid", dy=-14)
    p.edge("check", "stop", a_side="l", b_side="r", kind="reject", label="broken", dy=-14)
    return p


def secrets():
    p = Page("09-secrets", "Keeping secrets", 720, 470, "Where the passwords live, and where they never go",
             "Application passwords live in group_vars/all/vault.yml, which is encrypted, so Git only ever stores scrambled text. The "
             "password that unlocks it is a Jenkins credential. The Aurora database's admin login is read from AWS Secrets Manager at run "
             "time. The SSH key is pulled from Terraform for the run and deleted afterwards. On the servers, secrets are written to files "
             "only root can read, and Ansible hides them from its log.")
    p.zone("Stored safely", 15, 12, 260, 446)
    p.node("vault", "bus", 30, 40, 230, 72, "vault.yml (in Git)", "app passwords, encrypted:", "scrambled text in Git")
    p.node("vpw", "browser", 30, 140, 230, 72, "Jenkins credential", "the password that", "unlocks vault.yml")
    p.node("sm", "external", 30, 240, 230, 72, "AWS Secrets Manager", "rdscreds: the Aurora", "admin login")
    p.node("key", "agent", 30, 340, 230, 88, "SSH key", "taken from Terraform", "for the run, then deleted", "(never committed)")
    p.node("run", "gateway", 305, 170, 180, 120, "Ansible run", "unlocks secrets", "in memory only", "", "no_log: hides them", )
    p.zone("On each server", 515, 12, 190, 446)
    p.node("env", "store", 525, 186, 170, 88, "/etc/roboshop/", "shipping.env etc.", "readable by root only", "(mode 0600)")
    p.node("svc", "service", 525, 320, 170, 72, "The service", "reads its passwords", "when it starts")
    p.edge("vault", "run", a_side="r", b_side="l", b_at=0.2, kind="dashed")
    p.edge("vpw", "run", a_side="r", b_side="l", b_at=0.4, kind="dashed")
    p.edge("sm", "run", a_side="r", b_side="l", b_at=0.6, kind="dashed")
    p.edge("key", "run", a_side="r", b_side="l", b_at=0.8, kind="dashed")
    p.edge("run", "env", a_side="r", b_side="l", kind="write", label="writes", dy=-12)
    p.edge("env", "svc")
    return p


def pipeline():
    p = Page("10-pipeline", "Jenkins pipeline", 720, 470, "One Jenkins job, four buttons",
             "The Jenkins job asks for an ACTION. Plan checks the code and shows what Terraform would change. CreateInfra checks, plans, "
             "waits for a person to approve, builds the servers, builds the shipping app and runs Ansible. DeployApp skips Terraform and "
             "runs Ansible against the servers that already exist. DeleteInfra plans the removal, waits for approval and deletes "
             "everything. Every run ends by deleting the SSH key and the plan file.")
    cols = {
        "Plan": [("external", "Lint", "check the code"), ("agent", "Terraform plan", "show the changes"),
                 ("absent", "Stop", "nothing is changed")],
        "CreateInfra": [("external", "Lint", "check the code"), ("agent", "Terraform plan", "show the changes"),
                        ("browser", "Approve", "a person clicks Apply"), ("agent", "Terraform apply", "build the servers"),
                        ("mcp", "Build shipping", "Maven makes the jar"), ("gateway", "Run Ansible", "roboshop.yml")],
        "DeployApp": [("external", "Lint", "check the code"), ("mcp", "Build shipping", "Maven makes the jar"),
                      ("gateway", "Run Ansible", "roboshop.yml")],
        "DeleteInfra": [("external", "Lint", "check the code"), ("agent", "Destroy plan", "list what goes"),
                        ("browser", "Approve", "a person clicks Apply"), ("reject", "Terraform apply", "delete everything")],
    }
    for c, (action, stages) in enumerate(cols.items()):
        x = 15 + c * 175
        p.zone(action, x, 12, 165, 380)
        for r, (kind, title, line) in enumerate(stages):
            p.node(f"s{c}{r}", kind, x + 10, 40 + r * 58, 145, 44, title, line)
            if r:
                p.edge(f"s{c}{r - 1}", f"s{c}{r}")
    p.node("clean", "bus", 15, 408, 690, 48, "Always, at the end", "delete the SSH key (roboshop.pem) and the Terraform plan file")
    return p


def push_pull():
    p = Page("11-push-pull", "Push and pull", 720, 360, "Two ways to run the same playbook",
             "Push is how this repository normally runs: the control machine connects out to every server with ansible-playbook. Pull is "
             "the alternative: a single server downloads the repository from GitHub with ansible-pull and runs the playbook on itself, "
             "told which component it is with roboshop_component=cart.")
    p.zone("Push: ansible-playbook (the normal way)", 15, 12, 335, 336)
    p.node("ctl", "gateway", 30, 44, 305, 64, "Control machine", "ansible-playbook roboshop.yml")
    for i, name in enumerate(("cart", "user", "payment")):
        p.node(f"p{name}", "service", 30 + i * 105, 250, 95, 44, name)
        p.edge("ctl", f"p{name}", a_at=0.2 + i * 0.3, label="SSH" if i == 1 else "")
    p.zone("Pull: ansible-pull (one server helps itself)", 370, 12, 335, 336)
    p.node("gh", "external", 385, 44, 305, 64, "GitHub", "github.com/mrjithendar/Ansible")
    p.node("srv", "service", 385, 220, 305, 104, "The cart server", "downloads the repository, then runs", "roboshop.yml on itself with",
           "-e roboshop_component=cart", "(no control machine needed)")
    p.edge("srv", "gh", a_side="t", b_side="b", label="git clone")
    return p


FILES = {
    "01-big-picture": big_picture,
    "02-building-blocks": building_blocks,
    "03-repo-map": repo_map,
    "04-inventory": inventory,
    "05-play-order": play_order,
    "06-role-anatomy": role_anatomy,
    "07-idempotency": idempotency,
    "08-handlers": handlers,
    "09-secrets": secrets,
    "10-pipeline": pipeline,
    "11-push-pull": push_pull,
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    built = []
    for name, make in FILES.items():
        page = make()
        for e in page.edges:
            for x, y in e["points"]:
                if not (0 <= x <= page.w and 0 <= y <= page.h):
                    raise SystemExit(f"{page.figure}: edge {e['id']} leaves the page")
        for n in page.nodes.values():
            if n["x"] < 0 or n["y"] < 0 or n["x"] + n["w"] > page.w or n["y"] + n["h"] > page.h:
                raise SystemExit(f"{page.figure}: {n['id']} leaves the page")
        mxfile = ET.Element("mxfile", host="app.diagrams.net", agent="build_diagrams.py", version="24.7.17", type="device")
        mxfile.append(series.page_xml(page, 0))
        ET.indent(mxfile)
        (HERE / f"{name}.drawio").write_bytes(ET.tostring(mxfile, encoding="utf-8", xml_declaration=False))
        (OUT / f"{page.figure}.svg").write_text(series.page_svg(page), encoding="utf-8")
        built.append((page.figure, page.w, page.h))
    (HERE / "figures.txt").write_text("".join(f"{f} {w} {h}\n" for f, w, h in built), encoding="utf-8")
    print("\n".join(f"{f}: {w}×{h}" for f, w, h in built))


if __name__ == "__main__":
    main()
