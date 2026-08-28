from staging.readiness import audited_count
assert audited_count() == 3
print('prefork check passed')
