import { Outlet, NavLink, Link } from "react-router-dom";

import github from "../../assets/github.svg";

import styles from "./Footer.module.css";

const Footer = () => {
    return (
        <div className={styles.Footer}>
            <header className={styles.header} role={"banner"}>
                <div className={styles.headerContainer}>
                    <h4 className={styles.headerRightText}>Power by @yanluohao 2023-03-24</h4>
                </div>
            </header>

            <Outlet />
        </div>
    );
};

export default Footer;
