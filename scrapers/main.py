import scrape
import cli
import util


def main():
    util.make_dirs()
    args = cli.parse()
    scrape.scrape_all(args)


if __name__ == "__main__":
    main()
