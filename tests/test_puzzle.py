from chess import WHITE, BLACK
from puzzle import algo, go_to_move
from io import StringIO
from chess.pgn import read_game

pgn = StringIO("""[Event "Rated Blitz tournament https://lichess.org/tournament/oSyPykCM"]
[Site "https://lichess.org/OIR2O8JN"]
[White "Ayman22"]
[Black "daamien"]
[Result "1-0"]
[UTCDate "2016.01.31"]
[UTCTime "23:00:02"]
[WhiteElo "1364"]
[BlackElo "1414"]
[WhiteRatingDiff "+13"]
[BlackRatingDiff "-13"]
[ECO "B10"]
[Opening "Caro-Kann Defense: Two Knights Attack"]
[TimeControl "300+0"]
[Termination "Normal"]

1. e4 c6 2. Nf3 d5 3. Nc3 d4 4. Ne2 e5 5. c3 d3 6. Neg1 Bg4 7. h3 Bxf3 8. Nxf3 c5 9. Nxe5 c4 10. Qf3 Qf6 11. Qxf6 Nxf6 12. Nxc4 Be7 13. Bxd3 O-O 14. O-O Nc6 15. Re1 Rad8 16. e5 Rxd3 17. exf6 Bxf6 18. b3 Nb4 19. Ba3 Nc2 20. Bxf8 Kxf8 21. Nb2 Nxa1 22. Nxd3 Nc2 23. Rb1 1-0"""
               )


def test_go_to_move():
    game = read_game(pgn)
    test = go_to_move(game, 10, WHITE)
    assert test == "rn1qkbnr/pp3ppp/8/4N3/2p1P3/2Pp3P/PP1P1PP1/R1BQKB1R w KQkq - 0 10", test
    test1 = go_to_move(game, 10, BLACK)
    assert test1 == "rn1qkbnr/pp3ppp/8/4N3/2p1P3/2Pp1Q1P/PP1P1PP1/R1B1KB1R b KQkq - 1 10", test1
