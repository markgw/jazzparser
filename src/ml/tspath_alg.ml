(* Pseudocode ML version of algorithm. This won't run *)
type cadence = Point of int * int 
             | Leftonto of cadence
             | Rightonto of cadence
             | Coord of cadence list * cadence
             | CoordRes;;
type lf = cadence list;;

let cadence_path cad coordres = 
    match cad with 
    | Leftonto res -> 
            let respath = (get_cad_path res coordres) in
                (-1,0)+(hd respath)::respath
    | Rightonto res -> 
            let respath = (get_cad_path res coordres) in
                (1,0)+(hd respath)::respath
    | Point (x,y) -> [(x,y)]
    | Coord (pcads, res) -> 
            let respath = (get_cad_path res coordres) in
                (fold_left 
                    (fun base cad -> (remove_last
                     (get_cad_path cad (hd respath))) @ base)
                    [] (rev pcads)
                ) @ respath
    | CoordRes -> [coordres];;

let get_path lform =
    match lform with
    | cad::[] -> nearest_to (0,0) (cadence_path cad (0,0))
    | cad::cads -> let path2 = (get_path cads) in 
            (nearest_to (hd path2) (cadence_path cad)) @ path2;;
