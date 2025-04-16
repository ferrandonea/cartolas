from operator import mul
from functools import reduce


def multiply_list(lista: list[float]) -> float:
    return reduce(mul, lista, 1)


if __name__ == "__main__":
    print(multiply_list([1, 2, 3, 4, 5]))
    print(
        multiply_list(
            [
                1,
                2,
            ]
        )
    )
    print(multiply_list([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]))
