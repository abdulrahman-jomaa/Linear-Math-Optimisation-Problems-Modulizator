from modelBuilder import ModelBuilder


if __name__ == '__main__':
    model = ModelBuilder("model.json").build()
    model.optimize()

    print("Status:", model.getStatus())

    for v in model.getVars():
        val = model.getVal(v)
        if abs(val) > 1e-6:
            print(v.name, val)
