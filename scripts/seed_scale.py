import os, random
from datetime import date, timedelta
import psycopg

DATABASE_URL = os.environ.get("DATABASE_URL", "postgres://postgres@localhost:5432/brightloop")

def add_days(d, n):
    return (d + timedelta(days=n))

def main():
    conn = psycopg.connect(DATABASE_URL, autocommit=True)
    cur = conn.cursor()

    # Reset everything
    tables = ["payments","discount_redemptions","invoice_lines","invoices",
              "billing_run_items","billing_runs","subscription_pauses",
              "subscription_discounts","subscriptions","discounts",
              "subscription_lines","product_plan_prices",
              "quotation_template_lines","quotation_templates",
              "product_variants","taxes","payment_terms","products",
              "users","customers","schema_migrations"]
    for t in tables:
        cur.execute(f"DELETE FROM {t}")
    cur.execute("ALTER SEQUENCE subscription_number_seq RESTART WITH 1")
    cur.execute("ALTER SEQUENCE invoice_number_seq RESTART WITH 1")

    # --- Products ---
    p_erp = _pk_insert(cur,"products",["name","type","sales_price_minor"],
                      [("ERP Suite","subscription",56000),
                       ("Zoho CRM","subscription",0),
                       ("Tally ERP","subscription",24000),
                       ("Analytics Add-on","addon",12000),
                       ("Support Add-on","addon",6000),
                       ("Books","subscription",0)])
    p_crm, p_tally = p_erp[1], p_erp[2]
    _cur_exec(cur,"INSERT INTO product_variants VALUES (%s,%s,%s,%s)",
              [erp_id,"brand","Odoo",56000,crm_id,"tier","standard",0,tally_id,"release","2024",0])

    # --- Taxes ---
    t_18 = _pk_insert(cur,"taxes",["name","rate_bps","inclusive"],
                      [("GST 18%",1800,False),("GST 5%",500,False),("CGST 9% Inc",900,True)])
    t_18_ids = {row[0]: row[1] for row in [t_18]}

    # --- Payment terms ---
    pt_ids = {}
    for name, days in [("Immediate",0),("Net 15",15),("Net 30",30)]:
        _cur_exec(cur,"INSERT INTO payment_terms VALUES (%s,%s) RETURNING id",
                  [(name,days)])
        pt_ids[name] = cur.fetchone()[0]

    # --- Plans ---
    p_month = _pk_insert(cur,"plans",["name","price_minor","billing_interval","interval_count",
                                       "min_quantity","available_from","available_to",
                                       "auto_close","allow_early_close","allow_pause","allow_renew","active"],
                       [("Monthly",0,"month",1,1,None,"2025-12-31",False,True,True,True,true),
                        ("Yearly",120000,"year",1,1,None,"2025-12-31",False,True,True,True,true),
                        ("Weekly Trial",0,"week",1,1,None,"2025-12-31",True,True,True,False,true),
                        ("Auto Close",0,"month",1,1,None,"2025-06-01",False,True,True,True,true)])
    p_m, p_y, p_w, p_ac = p_month

    # --- Customers (8000+) ---
    for i in range(8000):
        _cur_exec(cur,"INSERT INTO customers VALUES (%s,%s,%s,true)",
                  [f"Cust {i}", f"c{i%1000}@example.com", f"+91 98765 {i%100000:05d}"])

    # --- Users ---
    _cur_exec(cur,"INSERT INTO users VALUES (%s,%s,%s,true,null)",
              ["admin@example.com","hash","admin"])
    for e in ["staff1@example.com","staff2@example.com"]:
        _cur_exec(cur,"INSERT INTO users VALUES (%s,%s,%s,true,null)",[e,"hash","staff"])

    # --- Subscriptions ---
    states = ["draft","quotation","confirmed","active","closed"]
    for i in range(8000):
        cust = i % 8000 + 1
        plan = random.choice([p_m,p_y,p_w,p_ac])
        sd = add_days(date(2025,1,1), i % 365)
        if plan == p_m: ed = add_days(add_days(sd.replace(day=1),1),-1) + timedelta(days=31)
        elif plan == p_y: ed = add_days(sd,365)
        else: ed = add_days(sd,30)
        status = random.choice(states)
        pt = random.list(pt_ids.values())
        _cur_exec(cur,"INSERT INTO subscriptions VALUES (%s,%s,%s,%s,%s,%s,%s,false,1,%s)",
                  [f"SUB-{i+1:06d}",cst,plan,status,sd,ed,pt,random.randint(1,2)])

    # --- Subscription lines ---
    for i in range(8000):
        sid = i + 1
        pid = random.choice([p_erp,p_crm,p_tally])
        qty = random.randint(1,10)
        base = 10000 + random.randint(0,50000)
        price = base + (56000 if random.random()<0.7 else 0)
        tx = random.choice([t_18_ids["GST 18%"],None]) if random.random()<0.8 else None
        ico = random.choice([True,False])
        _cur_exec(cur,"INSERT INTO subscription_lines VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                  [sid,pid,random.randint(1,3) if random.random()<0.7 else None,qty,price,tx,1800 if tx else 0,ico])

    # --- Discounts ---
    _cur_exec(cur,"INSERT INTO discounts VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,true,true,0,30)",
            ["10% on >= 5 seats","percent",1000,5000,1,30,None,"product",True,True,30])
    _cur_exec(cur,"INSERT INTO discounts VALUES (%s,%s,%s,%s,%s,%s,%s,%s,true,true,0,30)",
            ["Fixed 500 off >= 5000","fixed",50000,None,None,30,None,"subscription",True,True,30])
    _cur_exec(cur,"INSERT INTO discounts VALUES (%s,%s,%s,%s,%s,%s,%s,%s,true,true,0,15)",
            ["Expiring 10%","percent",1000,None,None,15,p_erp[0],"product",True,True,15])

    # --- Subscription discounts ---
    for i in range(2000):
        _cur_exec(cur,"INSERT INTO subscription_discounts VALUES (%s,%s)",
                  [random.randint(1,8000),random.randint(1,3)])

    # --- Invoices (~60k) via generate_series approach ---
    base_d = date(2025,3,1)
    for i in range(60000):
        sub = random.randint(1,8000)
        pd = add_days(base_d, (i * 43 + sub) % 365)  # staggered periods
        ped = add_days(pd, 30)
        idate = add_days(pd, random.randint(0,3))
        ddue = add_days(idate, random.choice([0,15,30]))
        status = random.choices(["draft","confirmed","paid"],weights=[0.5,0.3,0.2])[0]
        subtotal = random.randint(500,50000)
        disc = random.randint(0,min(2000,subtotal))
        nb = random.choice([True,False])
        if nb:
            net = subtotal - disc
            tax = round(net * 1800 / 10000)
            total = net + tax
        else:
            gross = subtotal
            net = round(gross * 10000 / (10000 + 1800))
            tax = gross - net
            total = gross
        apaid = random.randint(0, total if status!="paid" else total)
        num = f"INV-{idate.year}-{i%100000:06d}"
        _cur_exec(cur,"INSERT INTO invoices VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,null)",
                  [num,sub,cust,pd,ped,idate,ddue,status,subtotal,disc,tax,total,apaid])

    # --- Invoice lines (~6 per invoice) ---
    for i in range(360000):
        inv = random.randint(1,60000)
        pid = random.choice([p_erp,p_crm,p_tally])
        qty = random.randint(1,5)
        up = random.randint(100,5000)
        ls = up * qty
        disc = random.randint(0,ls)
        nb = random.choice([True,False])
        if nb:
            net = ls - disc
            tax = round(net * 1800 / 10000)
            tot = net + tax
        else:
            gross = ls
            net = round(gross * 10000 / (10000 + 1800))
            tax = gross - net
            tot = gross
        pname = ["ERP Suite","Zoho CRM","Tally ERP"][pid%3]
        _cur_exec(cur,"INSERT INTO invoice_lines VALUES (%s,%s,null,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                  [inv,pid,qty,up,ls,disc,1800 if nb else 0,nb,tax,tot,f"{pname} x {qty}"])

    # --- Payments (~40k) ---
    for i in range(40000):
        inv = random.randint(1,60000)
        meth = random.choice(["cash","bank_transfer","card","upi","cheque","other"])
        amt = random.randint(1,50000)
        pod = add_days(date(2025,3,1), i % 61)
        _cur_exec(cur,"INSERT INTO payments VALUES (%s,%s,%s,%s,%s,%s,idemp_%s)",
                  [inv,meth,amt,pod,f"Note {i}",random.randint(1,3),i])

    # --- Billing runs ---
    for i in range(5):
        _cur_exec(cur,"INSERT INTO billing_runs VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'{}')",
                  ["live",add_days(date(2025,6,1),i),"completed",1,
                   random.randint(100,500),random.randint(50,200),
                   random.randint(1000,50000),0])

    # --- Verify invariants ---
    ic = cur.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
    sc = cur.execute("SELECT COUNT(*) FROM subscriptions").fetchone()[0]
    pc = cur.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
    print(f"Scale seed: {sc} subs, {ic} invoices, {pc} payments")

    cur.close()
    conn.close()

def _pk_insert(cur,table,cols,rows):
    _cur_exec(cur,f"INSERT INTO {table} ({','.join(cols)}) VALUES (%s,%s,%s) RETURNING id", rows[0])
    return cur.fetchone()[0]

def _cur_exec(cur,sql,params=None):
    if params:
        cur.execute(sql,params)
    else:
        cur.execute(sql)

main()