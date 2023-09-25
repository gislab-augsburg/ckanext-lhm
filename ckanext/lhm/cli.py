import click


@click.group(short_help="lhm CLI.")
def lhm():
    """lhm CLI.
    """
    pass


@lhm.command()
@click.argument("name", default="lhm")
def command(name):
    """Docs.
    """
    click.echo("Hello, {name}!".format(name=name))


def get_commands():
    return [lhm]
